"""Universe Loader — auto-discovery of ALL tradeable instruments on MOEX.

Loads ALL stocks from TQBR board and ALL futures from FORTS,
then filters by liquidity (ADV, spread, open interest).

No hardcoded ticker lists. The universe is rebuilt every trading day.

Data sources:
    Stocks:   https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json
    Futures:  https://iss.moex.com/iss/engines/futures/markets/forts/securities.json
    Indices:  https://iss.moex.com/iss/engines/stock/markets/index/securities.json
    Candles:  https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}/candles.json

All endpoints are FREE, no API key, no rate limits.

Public API:
    load_all_stocks() -> list[Instrument]
    load_all_futures() -> list[Instrument]
    load_full_universe(min_adv=50_000_000) -> Universe
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger(__name__)

ISS_BASE = "https://iss.moex.com/iss"

# Sector classification by MOEX listing
SECTOR_KEYWORDS: dict[str, list[str]] = {
    "oil_gas": ["нефт", "газ", "oil", "gas", "энерг", "лукойл", "роснефть", "газпром", "новатэк", "сургут", "татнефт", "транснефт", "башнефт"],
    "banks": ["банк", "финанс", "биржа", "страхов", "тинькофф", "сбер", "втб"],
    "metals": ["никель", "сталь", "металл", "алроса", "полюс", "русал", "ммк", "нлмк", "полиметалл", "норильск"],
    "it": ["яндекс", "ozon", "vk", "mail", "цифр", "технолог", "программ", "софт"],
    "retail": ["магнит", "x5", "лента", "детский", "ритейл", "торгов"],
    "telecom": ["мтс", "ростелеком", "мегафон", "связь", "телеком"],
    "chemicals": ["фосагро", "акрон", "уралкалий", "химич", "удобрен"],
    "real_estate": ["пик", "самолёт", "девелоп", "строител", "недвижим", "эталон", "лср"],
    "energy": ["интер рао", "русгидро", "электро", "энерго", "юнипро", "оэк"],
    "transport": ["аэрофлот", "совкомфлот", "транспорт", "авиа", "флот", "nmtp"],
}


@dataclass(frozen=True)
class Instrument:
    """A tradeable instrument on MOEX."""

    ticker: str
    name: str
    type: str  # "stock" | "futures"
    board: str  # "TQBR" | "FORTS"
    sector: str
    lot_size: int
    last_price: float
    volume_today: float  # в рублях
    adv_20: float  # 20-day average daily volume (руб)
    spread_pct: float  # bid-ask spread %
    open_interest: int  # only for futures


@dataclass
class Universe:
    """Full tradeable universe with metadata."""

    stocks: list[Instrument] = field(default_factory=list)
    futures: list[Instrument] = field(default_factory=list)
    indices: list[str] = field(default_factory=list)
    timestamp: str = ""

    @property
    def all_instruments(self) -> list[Instrument]:
        return self.stocks + self.futures

    @property
    def stock_tickers(self) -> list[str]:
        return [s.ticker for s in self.stocks]

    @property
    def futures_tickers(self) -> list[str]:
        return [f.ticker for f in self.futures]

    def top_by_adv(self, n: int = 50) -> list[Instrument]:
        """Top N instruments by average daily volume."""
        return sorted(self.all_instruments, key=lambda x: x.adv_20, reverse=True)[:n]


def _classify_sector(name: str) -> str:
    """Classify instrument sector from its name."""
    name_lower = name.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return sector
    return "other"


async def _fetch_json(session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    """Fetch JSON from MOEX ISS API."""
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        resp.raise_for_status()
        return await resp.json()


async def load_all_stocks(
    session: aiohttp.ClientSession | None = None,
) -> list[Instrument]:
    """Load ALL stocks from MOEX TQBR board.

    Returns every stock currently listed on the main board,
    with current price, volume, and basic metadata.

    Source: MOEX ISS /engines/stock/markets/shares/boards/TQBR/securities.json
    """
    close_session = session is None
    if session is None:
        session = aiohttp.ClientSession()

    instruments: list[Instrument] = []

    try:
        url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off"
        data = await _fetch_json(session, url)

        securities = data.get("securities", {})
        sec_columns = securities.get("columns", [])
        sec_data = securities.get("data", [])

        marketdata = data.get("marketdata", {})
        md_columns = marketdata.get("columns", [])
        md_data = marketdata.get("data", [])

        # Build column index maps
        sec_idx = {col: i for i, col in enumerate(sec_columns)}
        md_idx = {col: i for i, col in enumerate(md_columns)}

        # Build marketdata lookup by SECID
        md_lookup: dict[str, list] = {}
        for row in md_data:
            secid = row[md_idx.get("SECID", 0)]
            if secid:
                md_lookup[str(secid)] = row

        for row in sec_data:
            ticker = str(row[sec_idx.get("SECID", 0)] or "")
            if not ticker:
                continue

            name = str(row[sec_idx.get("SHORTNAME", 1)] or ticker)
            lot_size = int(row[sec_idx.get("LOTSIZE", 2)] or 1)

            md_row = md_lookup.get(ticker)
            last_price = 0.0
            volume_rub = 0.0

            if md_row:
                last_price = float(md_row[md_idx.get("LAST", 0)] or 0)
                volume_rub = float(md_row[md_idx.get("VALTODAY", 0)] or 0)

            # Spread: (ask - bid) / mid
            spread_pct = 0.0
            if md_row:
                bid = float(md_row[md_idx.get("BID", 0)] or 0)
                ask = float(md_row[md_idx.get("OFFER", 0)] or 0)
                if bid > 0 and ask > 0:
                    spread_pct = (ask - bid) / ((ask + bid) / 2) * 100

            sector = _classify_sector(name)

            instruments.append(Instrument(
                ticker=ticker,
                name=name,
                type="stock",
                board="TQBR",
                sector=sector,
                lot_size=lot_size,
                last_price=last_price,
                volume_today=volume_rub,
                adv_20=volume_rub,  # approximation; TODO: load 20-day avg
                spread_pct=round(spread_pct, 4),
                open_interest=0,
            ))

        logger.info("universe.stocks_loaded", count=len(instruments))

    except Exception as e:
        logger.error("universe.stocks_error", error=str(e))
    finally:
        if close_session:
            await session.close()

    return instruments


async def load_all_futures(
    session: aiohttp.ClientSession | None = None,
) -> list[Instrument]:
    """Load ALL futures from MOEX FORTS.

    Source: MOEX ISS /engines/futures/markets/forts/securities.json
    """
    close_session = session is None
    if session is None:
        session = aiohttp.ClientSession()

    instruments: list[Instrument] = []

    try:
        url = f"{ISS_BASE}/engines/futures/markets/forts/securities.json?iss.meta=off"
        data = await _fetch_json(session, url)

        securities = data.get("securities", {})
        sec_columns = securities.get("columns", [])
        sec_data = securities.get("data", [])

        marketdata = data.get("marketdata", {})
        md_columns = marketdata.get("columns", [])
        md_data = marketdata.get("data", [])

        sec_idx = {col: i for i, col in enumerate(sec_columns)}
        md_idx = {col: i for i, col in enumerate(md_columns)}

        md_lookup: dict[str, list] = {}
        for row in md_data:
            secid_col = md_idx.get("SECID", 0)
            secid = row[secid_col] if secid_col < len(row) else None
            if secid:
                md_lookup[str(secid)] = row

        for row in sec_data:
            secid_col = sec_idx.get("SECID", 0)
            ticker = str(row[secid_col] if secid_col < len(row) else "")
            if not ticker:
                continue

            shortname_col = sec_idx.get("SHORTNAME", 1)
            name = str(row[shortname_col] if shortname_col < len(row) else ticker)

            lot_size = 1
            lotvol_col = sec_idx.get("LOTVOLUME")
            if lotvol_col is not None and lotvol_col < len(row):
                try:
                    lot_size = int(row[lotvol_col] or 1)
                except (ValueError, TypeError):
                    lot_size = 1

            md_row = md_lookup.get(ticker)
            last_price = 0.0
            volume_rub = 0.0
            oi = 0

            if md_row:
                def _safe_float(col_name: str) -> float:
                    idx = md_idx.get(col_name)
                    if idx is not None and idx < len(md_row):
                        try:
                            return float(md_row[idx] or 0)
                        except (ValueError, TypeError):
                            return 0.0
                    return 0.0

                def _safe_int(col_name: str) -> int:
                    idx = md_idx.get(col_name)
                    if idx is not None and idx < len(md_row):
                        try:
                            return int(float(md_row[idx] or 0))
                        except (ValueError, TypeError):
                            return 0
                    return 0

                last_price = _safe_float("LAST")
                volume_rub = _safe_float("VALTODAY")
                oi = _safe_int("OPENPOSITIONS")

            # Determine sector from underlying
            sector = "futures"
            name_lower = name.lower()
            if "si" in ticker.lower()[:2] or "usd" in name_lower:
                sector = "fx_futures"
            elif "br" in ticker.lower()[:2] or "brent" in name_lower:
                sector = "commodity_futures"
            elif "ri" in ticker.lower()[:2] or "rts" in name_lower:
                sector = "index_futures"
            elif "sr" in ticker.lower()[:2] or "сбер" in name_lower:
                sector = "stock_futures"
            elif "gz" in ticker.lower()[:2] or "газпром" in name_lower:
                sector = "stock_futures"

            instruments.append(Instrument(
                ticker=ticker,
                name=name,
                type="futures",
                board="FORTS",
                sector=sector,
                lot_size=lot_size,
                last_price=last_price,
                volume_today=volume_rub,
                adv_20=volume_rub,
                spread_pct=0.0,
                open_interest=oi,
            ))

        logger.info("universe.futures_loaded", count=len(instruments))

    except Exception as e:
        logger.error("universe.futures_error", error=str(e))
    finally:
        if close_session:
            await session.close()

    return instruments


async def load_full_universe(
    min_adv_stocks: float = 50_000_000,  # 50M руб минимальный ADV
    min_adv_futures: float = 10_000_000,  # 10M руб для фьючерсов
    min_open_interest: int = 500,  # минимальный OI для фьючерсов
    max_spread_pct: float = 1.0,  # максимальный спред %
    session: aiohttp.ClientSession | None = None,
) -> Universe:
    """Load and filter full MOEX universe.

    Fetches ALL stocks and futures, then filters by:
    - Stocks: ADV >= 50M RUB, spread < 1%
    - Futures: ADV >= 10M RUB, open interest >= 500

    Parameters
    ----------
    min_adv_stocks: Minimum average daily volume for stocks (RUB).
    min_adv_futures: Minimum ADV for futures (RUB).
    min_open_interest: Minimum open interest for futures.
    max_spread_pct: Maximum bid-ask spread %.

    Returns
    -------
    Universe with filtered stocks and futures.
    """
    close_session = session is None
    if session is None:
        session = aiohttp.ClientSession()

    try:
        stocks = await load_all_stocks(session)
        futures = await load_all_futures(session)
    finally:
        if close_session:
            await session.close()

    # Filter stocks
    filtered_stocks = [
        s for s in stocks
        if s.adv_20 >= min_adv_stocks
        and s.spread_pct <= max_spread_pct
        and s.last_price > 0
    ]

    # Filter futures
    filtered_futures = [
        f for f in futures
        if f.adv_20 >= min_adv_futures
        and f.open_interest >= min_open_interest
        and f.last_price > 0
    ]

    from datetime import datetime
    universe = Universe(
        stocks=sorted(filtered_stocks, key=lambda x: x.adv_20, reverse=True),
        futures=sorted(filtered_futures, key=lambda x: x.adv_20, reverse=True),
        timestamp=datetime.now().isoformat(),
    )

    logger.info(
        "universe.loaded",
        total_stocks=len(stocks),
        filtered_stocks=len(filtered_stocks),
        total_futures=len(futures),
        filtered_futures=len(filtered_futures),
        top5_stocks=[s.ticker for s in universe.stocks[:5]],
        top5_futures=[f.ticker for f in universe.futures[:5]],
    )

    return universe
