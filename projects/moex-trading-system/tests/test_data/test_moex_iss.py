"""Tests for MOEX ISS client.

Uses REAL requests to MOEX ISS (free API, no key required).
Tests are skipped if no network access.
"""
from __future__ import annotations

import asyncio
import socket
from datetime import date, timedelta

import pytest

from src.data.moex_iss import MoexISSClient


def _has_network() -> bool:
    """Check if we have internet access to MOEX."""
    try:
        socket.create_connection(("iss.moex.com", 443), timeout=3)
        return True
    except (OSError, socket.timeout):
        return False


no_network = not _has_network()
skip_no_net = pytest.mark.skipif(no_network, reason="No network access to MOEX ISS")


@pytest.fixture
def client():
    return MoexISSClient()


@skip_no_net
class TestMoexISS:
    def test_fetch_candles_sber(self, client):
        """Fetch SBER candles for last month."""
        end = date.today()
        start = end - timedelta(days=30)

        async def _run():
            async with client:
                return await client.fetch_candles("SBER", start, end)

        bars = asyncio.run(_run())
        assert len(bars) > 0, "Should fetch at least one candle"
        assert bars[0].instrument == "SBER"

    def test_fetch_candles_si(self, client):
        """Fetch futures Si candles."""
        end = date.today()
        start = end - timedelta(days=30)

        async def _run():
            async with client:
                return await client.fetch_futures_candles("SiH5", start, end)

        bars = asyncio.run(_run())
        # Futures tickers change with expiry, may be empty
        assert isinstance(bars, list)

    def test_fetch_candles_pagination(self, client):
        """Fetch > 500 candles (triggers auto-pagination)."""
        end = date.today()
        start = end - timedelta(days=1000)

        async def _run():
            async with client:
                return await client.fetch_candles("SBER", start, end)

        bars = asyncio.run(_run())
        assert len(bars) > 500, f"Expected >500 candles, got {len(bars)}"

    def test_candles_have_all_fields(self, client):
        """Each candle has timestamp, OHLCV, instrument."""
        end = date.today()
        start = end - timedelta(days=7)

        async def _run():
            async with client:
                return await client.fetch_candles("SBER", start, end)

        bars = asyncio.run(_run())
        if bars:
            bar = bars[0]
            assert bar.timestamp is not None
            assert bar.open > 0
            assert bar.high > 0
            assert bar.low > 0
            assert bar.close > 0
            assert bar.volume >= 0
            assert bar.instrument == "SBER"

    def test_candles_sorted_by_time(self, client):
        """Candles in chronological order."""
        end = date.today()
        start = end - timedelta(days=30)

        async def _run():
            async with client:
                return await client.fetch_candles("SBER", start, end)

        bars = asyncio.run(_run())
        if len(bars) > 1:
            for i in range(1, len(bars)):
                assert bars[i].timestamp >= bars[i - 1].timestamp

    def test_fetch_instruments(self, client):
        """List of TQBR instruments is not empty."""
        async def _run():
            async with client:
                return await client.fetch_instruments()

        instruments = asyncio.run(_run())
        assert len(instruments) > 0, "TQBR should have instruments"

    def test_fetch_imoex(self, client):
        """IMOEX index candles load."""
        end = date.today()
        start = end - timedelta(days=30)

        async def _run():
            async with client:
                return await client.fetch_index("IMOEX", start, end)

        bars = asyncio.run(_run())
        assert isinstance(bars, list)

    def test_invalid_ticker(self, client):
        """Non-existent ticker returns empty result."""
        async def _run():
            async with client:
                return await client.fetch_candles("ZZZZZZZ", "2024-01-01", "2024-01-31")

        bars = asyncio.run(_run())
        assert len(bars) == 0

    def test_rate_limiting(self, client):
        """Multiple rapid requests don't cause 429."""
        end = date.today()
        start = end - timedelta(days=5)

        async def _run():
            async with client:
                tasks = [
                    client.fetch_candles("SBER", start, end)
                    for _ in range(10)
                ]
                results = await asyncio.gather(*tasks)
                return results

        results = asyncio.run(_run())
        assert all(isinstance(r, list) for r in results)

    def test_to_polars(self, client):
        """Bars convert to Polars DataFrame."""
        end = date.today()
        start = end - timedelta(days=7)

        async def _run():
            async with client:
                bars = await client.fetch_candles("SBER", start, end)
                return client.to_polars(bars)

        df = asyncio.run(_run())
        assert "close" in df.columns
        assert "timestamp" in df.columns
        if df.height > 0:
            assert df["close"][0] > 0
