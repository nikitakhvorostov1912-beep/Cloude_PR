"""MOEX ISS REST API client for market data.

Supports candles, instruments, orderbook, and index data.
Rate limiting via asyncio semaphore (50 req/sec).
Auto-pagination for large date ranges (MOEX returns max 500 rows per request).
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

import aiohttp
import polars as pl
import structlog

from src.core.config import load_settings
from src.core.models import Bar

logger = structlog.get_logger(__name__)

# MOEX ISS timeframe mapping
TIMEFRAME_MAP = {
    "1m": 1,
    "10m": 10,
    "1h": 60,
    "1d": 24,
    "1w": 7,
    "1M": 31,
}


class MoexISSClient:
    """Async client for MOEX ISS REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        max_requests_per_sec: int | None = None,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ):
        try:
            cfg = load_settings()
            self._base_url = base_url or cfg.moex.iss_url
            self._max_rps = max_requests_per_sec or cfg.moex.max_requests_per_sec
        except FileNotFoundError:
            self._base_url = base_url or "https://iss.moex.com/iss"
            self._max_rps = max_requests_per_sec or 50

        self._semaphore = asyncio.Semaphore(self._max_rps)
        self._retry_count = retry_count
        self._retry_delay = retry_delay
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, url: str, params: dict[str, Any] | None = None) -> dict:
        """Make a rate-limited request with retries.

        ISS with iss.json=extended returns: [{charsetinfo}, {block: [row_dicts]}]
        We normalize to: {block: [row_dicts]} for easier extraction.
        """
        session = await self._get_session()
        full_params = {"iss.json": "extended", "iss.meta": "off"}
        if params:
            full_params.update(params)

        for attempt in range(self._retry_count):
            async with self._semaphore:
                try:
                    async with session.get(url, params=full_params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            raw = await resp.json(content_type=None)
                            # Normalize: ISS extended returns list of dicts
                            if isinstance(raw, list):
                                merged: dict[str, Any] = {}
                                for item in raw:
                                    if isinstance(item, dict):
                                        merged.update(item)
                                return merged
                            return raw if isinstance(raw, dict) else {}
                        if resp.status == 429:
                            wait = self._retry_delay * (2 ** attempt)
                            logger.warning("Rate limited, retrying", wait=wait)
                            await asyncio.sleep(wait)
                            continue
                        logger.error("HTTP error", status=resp.status, url=url)
                        return {}
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt < self._retry_count - 1:
                        wait = self._retry_delay * (2 ** attempt)
                        logger.warning("Request failed, retrying", error=str(e), wait=wait)
                        await asyncio.sleep(wait)
                    else:
                        logger.error("Request failed after retries", error=str(e))
                        return {}
        return {}

    async def fetch_candles(
        self,
        ticker: str,
        start: date | str,
        end: date | str,
        timeframe: str = "1d",
        board: str = "TQBR",
        engine: str = "stock",
        market: str = "shares",
    ) -> list[Bar]:
        """Fetch OHLCV candles with auto-pagination.

        MOEX ISS returns max 500 candles per request.
        We paginate until all data is fetched.
        """
        interval = TIMEFRAME_MAP.get(timeframe, 24)
        start_str = str(start)
        end_str = str(end)

        all_bars: list[Bar] = []
        page_start = 0
        page_size = 500

        while True:
            url = (
                f"{self._base_url}/engines/{engine}/markets/{market}"
                f"/boards/{board}/securities/{ticker}/candles.json"
            )
            params = {
                "from": start_str,
                "till": end_str,
                "interval": interval,
                "start": page_start,
            }

            data = await self._request(url, params)
            candles = self._extract_candles(data, ticker, timeframe)

            if not candles:
                break

            all_bars.extend(candles)

            if len(candles) < page_size:
                break

            page_start += len(candles)

        # Sort by timestamp
        all_bars.sort(key=lambda b: b.timestamp)

        logger.info(
            "Fetched candles",
            ticker=ticker,
            count=len(all_bars),
            start=start_str,
            end=end_str,
        )
        return all_bars

    async def fetch_futures_candles(
        self,
        ticker: str,
        start: date | str,
        end: date | str,
        timeframe: str = "1d",
    ) -> list[Bar]:
        """Fetch futures candles from RFUD board."""
        return await self.fetch_candles(
            ticker, start, end, timeframe,
            board="RFUD", engine="futures", market="forts",
        )

    async def fetch_instruments(
        self, board: str = "TQBR", engine: str = "stock", market: str = "shares"
    ) -> list[dict[str, Any]]:
        """Fetch list of instruments on a given board."""
        url = (
            f"{self._base_url}/engines/{engine}/markets/{market}"
            f"/boards/{board}/securities.json"
        )
        data = await self._request(url)
        return self._extract_securities(data)

    async def fetch_orderbook(
        self,
        ticker: str,
        board: str = "TQBR",
        depth: int = 20,
        engine: str = "stock",
        market: str = "shares",
    ) -> dict[str, Any]:
        """Fetch current orderbook for a ticker."""
        url = (
            f"{self._base_url}/engines/{engine}/markets/{market}"
            f"/boards/{board}/securities/{ticker}/orderbook.json"
        )
        data = await self._request(url)
        return self._extract_orderbook(data)

    async def fetch_index(
        self,
        ticker: str = "IMOEX",
        start: date | str = "2020-01-01",
        end: date | str = "2025-12-31",
        timeframe: str = "1d",
    ) -> list[Bar]:
        """Fetch index candles (IMOEX, RTSI, etc.)."""
        return await self.fetch_candles(
            ticker, start, end, timeframe,
            board="SNDX", engine="stock", market="index",
        )

    def to_polars(self, bars: list[Bar]) -> pl.DataFrame:
        """Convert list of Bar to Polars DataFrame."""
        if not bars:
            return pl.DataFrame({
                "timestamp": [], "open": [], "high": [],
                "low": [], "close": [], "volume": [], "instrument": [],
            })
        return pl.DataFrame([b.model_dump() for b in bars])

    # ── Extractors ──────────────────────────────────────────────

    @staticmethod
    def _extract_candles(
        data: dict, ticker: str, timeframe: str
    ) -> list[Bar]:
        """Extract candles from ISS JSON response.

        With iss.json=extended, candles is a list of dicts:
        [{"open": .., "close": .., "high": .., "low": .., "volume": .., "begin": ..}, ...]
        """
        bars: list[Bar] = []
        if not data:
            return bars

        try:
            rows = data.get("candles", [])
            if not isinstance(rows, list):
                return bars

            for row in rows:
                try:
                    if isinstance(row, dict):
                        ts_str = row.get("begin") or row.get("end", "")
                        ts = datetime.fromisoformat(str(ts_str)) if ts_str else datetime.now()
                        bar = Bar(
                            timestamp=ts,
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=int(row.get("volume", 0)),
                            instrument=ticker,
                            timeframe=timeframe,
                        )
                        bars.append(bar)
                except (ValueError, TypeError, KeyError) as e:
                    logger.debug("Skipping invalid candle row", error=str(e))
        except (KeyError, TypeError) as e:
            logger.debug("Failed to extract candles", error=str(e))

        return bars

    @staticmethod
    def _extract_securities(data: dict) -> list[dict[str, Any]]:
        """Extract securities from ISS JSON response.

        With iss.json=extended, securities is a list of dicts directly.
        """
        if not data:
            return []
        try:
            rows = data.get("securities", [])
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        except (KeyError, TypeError):
            pass
        return []

    @staticmethod
    def _extract_orderbook(data: dict) -> dict[str, Any]:
        """Extract orderbook from ISS JSON response.

        With iss.json=extended, orderbook is a list of dicts.
        """
        if not data:
            return {"bids": [], "asks": []}
        try:
            rows = data.get("orderbook", [])
            if isinstance(rows, list):
                bids = [r for r in rows if isinstance(r, dict) and r.get("BUYSELL") == "B"]
                asks = [r for r in rows if isinstance(r, dict) and r.get("BUYSELL") == "S"]
                return {"bids": bids, "asks": asks}
        except (KeyError, TypeError):
            pass
        return {"bids": [], "asks": []}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
