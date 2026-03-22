"""Download historical MOEX candles and save as Parquet files.

Usage:
    python scripts/download_history.py --tickers SBER,GAZP,LKOH --start 2020-01-01 --end 2025-12-31 --output data/history/

Features:
- Incremental downloads (skips already-downloaded tickers if file exists)
- Parquet output (one file per ticker)
- Progress display
- Supports both equities (TQBR) and futures (RFUD)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import polars as pl
import structlog

from src.core.config import load_settings
from src.data.moex_iss import MoexISSClient

logger = structlog.get_logger(__name__)

# Futures tickers use different board
FUTURES_TICKERS = {"Si", "RTS", "BR", "GOLD", "NG"}


async def download_ticker(
    client: MoexISSClient,
    ticker: str,
    start: str,
    end: str,
    output_dir: Path,
    timeframe: str = "1d",
    force: bool = False,
) -> int:
    """Download candles for a single ticker.

    Returns number of bars downloaded.
    """
    output_file = output_dir / f"{ticker}.parquet"

    if output_file.exists() and not force:
        existing = pl.read_parquet(output_file)
        logger.info("Ticker already downloaded, skipping", ticker=ticker, rows=existing.height)
        return existing.height

    if ticker in FUTURES_TICKERS:
        bars = await client.fetch_futures_candles(ticker, start, end, timeframe)
    else:
        bars = await client.fetch_candles(ticker, start, end, timeframe)

    if not bars:
        logger.warning("No data for ticker", ticker=ticker)
        return 0

    df = client.to_polars(bars)

    # Save as Parquet
    output_dir.mkdir(parents=True, exist_ok=True)
    df.write_parquet(output_file)

    logger.info(
        "Downloaded",
        ticker=ticker,
        bars=len(bars),
        start=str(bars[0].timestamp.date()),
        end=str(bars[-1].timestamp.date()),
        file=str(output_file),
    )
    return len(bars)


async def main(
    tickers: list[str],
    start: str,
    end: str,
    output_dir: str,
    timeframe: str = "1d",
    force: bool = False,
) -> dict[str, int]:
    """Download history for multiple tickers.

    Returns dict of ticker -> bar_count.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results: dict[str, int] = {}

    async with MoexISSClient() as client:
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] Downloading {ticker}...")
            count = await download_ticker(
                client, ticker, start, end, output_path, timeframe, force
            )
            results[ticker] = count

    # Summary
    total = sum(results.values())
    print(f"\nDone! Downloaded {total} bars for {len(results)} tickers.")
    for ticker, count in results.items():
        status = f"  {ticker}: {count} bars"
        if count == 0:
            status += " (no data)"
        print(status)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download MOEX historical data")
    parser.add_argument(
        "--tickers", required=True,
        help="Comma-separated list of tickers (e.g., SBER,GAZP,LKOH)",
    )
    parser.add_argument("--start", default="2020-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=str(date.today()), help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default="data/history/", help="Output directory")
    parser.add_argument("--timeframe", default="1d", help="Timeframe (1m, 10m, 1h, 1d)")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    tickers = [t.strip() for t in args.tickers.split(",")]
    asyncio.run(main(tickers, args.start, args.end, args.output, args.timeframe, args.force))
