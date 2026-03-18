"""Load historical candles for ALL liquid MOEX stocks.

Fetches candle data from MOEX ISS API for every stock on TQBR board
with sufficient volume, going back 1 year. Saves to SQLite.

Usage:
    python scripts/load_full_universe_data.py
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import aiohttp

ISS_BASE = "https://iss.moex.com/iss"
DB_PATH = Path("data/trading.db")
START_DATE = (date.today() - timedelta(days=365)).isoformat()  # 1 year back
END_DATE = date.today().isoformat()


async def fetch_all_tqbr_tickers(session: aiohttp.ClientSession) -> list[dict]:
    """Get ALL stock tickers from TQBR board."""
    url = f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off"
    async with session.get(url) as resp:
        data = await resp.json()

    securities = data.get("securities", {})
    columns = securities.get("columns", [])
    rows = securities.get("data", [])

    marketdata = data.get("marketdata", {})
    md_columns = marketdata.get("columns", [])
    md_rows = marketdata.get("data", [])

    col_idx = {c: i for i, c in enumerate(columns)}
    md_idx = {c: i for i, c in enumerate(md_columns)}

    md_lookup = {}
    for r in md_rows:
        secid = r[md_idx.get("SECID", 0)]
        if secid:
            md_lookup[str(secid)] = r

    tickers = []
    for r in rows:
        ticker = str(r[col_idx.get("SECID", 0)] or "")
        if not ticker:
            continue
        name = str(r[col_idx.get("SHORTNAME", 1)] or ticker)
        lot_size = 1
        try:
            lot_size = int(r[col_idx.get("LOTSIZE", 2)] or 1)
        except (ValueError, TypeError):
            pass

        md = md_lookup.get(ticker)
        volume = float(md[md_idx.get("VALTODAY", 0)] or 0) if md else 0

        tickers.append({"ticker": ticker, "name": name, "lot_size": lot_size, "volume_today": volume})

    return tickers


async def fetch_candles(
    session: aiohttp.ClientSession,
    ticker: str,
    start: str,
    end: str,
) -> list[dict]:
    """Fetch daily candles for a ticker from MOEX ISS."""
    all_candles = []
    cursor = 0

    while True:
        url = (
            f"{ISS_BASE}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}/candles.json"
            f"?from={start}&till={end}&interval=24&iss.meta=off&start={cursor}"
        )
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    break
                data = await resp.json()
        except Exception:
            break

        candles_block = data.get("candles", {})
        columns = candles_block.get("columns", [])
        rows = candles_block.get("data", [])

        if not rows:
            break

        col_idx = {c: i for i, c in enumerate(columns)}

        for r in rows:
            try:
                dt = str(r[col_idx.get("begin", 0)] or "")[:10]
                o = float(r[col_idx.get("open", 1)] or 0)
                h = float(r[col_idx.get("high", 3)] or 0)
                l = float(r[col_idx.get("low", 4)] or 0)
                c = float(r[col_idx.get("close", 2)] or 0)
                v = float(r[col_idx.get("volume", 5)] or 0)
                val = float(r[col_idx.get("value", 6)] or 0)

                if c > 0 and dt:
                    all_candles.append({
                        "ticker": ticker, "date": dt,
                        "open": o, "high": h, "low": l, "close": c,
                        "volume": v, "value": val, "source": "moex_iss",
                    })
            except (ValueError, TypeError, IndexError):
                continue

        cursor += len(rows)
        if len(rows) < 500:
            break

    return all_candles


def save_candles_batch(candles: list[dict]) -> int:
    """Save candles to SQLite with upsert."""
    if not candles:
        return 0

    conn = sqlite3.connect(DB_PATH)
    saved = 0
    for c in candles:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO candles
                   (ticker, date, open, high, low, close, volume, value, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (c["ticker"], c["date"], c["open"], c["high"], c["low"],
                 c["close"], c["volume"], c["value"], c["source"]),
            )
            saved += 1
        except sqlite3.Error:
            continue

    conn.commit()
    conn.close()
    return saved


async def main() -> None:
    print("=" * 70)
    print(f"  Loading ALL MOEX TQBR candles: {START_DATE} to {END_DATE}")
    print("=" * 70)

    # Also load IMOEX index
    index_tickers = ["IMOEX"]

    async with aiohttp.ClientSession() as session:
        # Step 1: Get all tickers
        print("\n[1/3] Fetching all TQBR tickers...")
        all_tickers = await fetch_all_tqbr_tickers(session)
        print(f"  Total tickers on TQBR: {len(all_tickers)}")

        # Filter by volume (at least traded today or in recent history)
        # We load ALL that have any price, filter later by actual history
        active_tickers = [t for t in all_tickers if True]  # load everything
        print(f"  Will load candles for: {len(active_tickers)} tickers + IMOEX")

        # Step 2: Load candles
        print(f"\n[2/3] Loading candles ({START_DATE} to {END_DATE})...")

        total_saved = 0
        total_tickers_loaded = 0
        failed = []

        # Load in batches of 10 (be nice to MOEX)
        ticker_list = [t["ticker"] for t in active_tickers] + index_tickers
        batch_size = 10

        for batch_start in range(0, len(ticker_list), batch_size):
            batch = ticker_list[batch_start:batch_start + batch_size]

            tasks = [fetch_candles(session, t, START_DATE, END_DATE) for t in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for ticker, result in zip(batch, results):
                if isinstance(result, Exception):
                    failed.append(ticker)
                    continue

                if result:
                    saved = save_candles_batch(result)
                    total_saved += saved
                    total_tickers_loaded += 1
                    if saved > 0:
                        sys.stdout.write(f"\r  {total_tickers_loaded} tickers loaded, {total_saved} candles saved... ({ticker}: {saved} bars)")
                        sys.stdout.flush()

            # Small delay between batches
            await asyncio.sleep(0.2)

        print(f"\n\n  Tickers loaded: {total_tickers_loaded}")
        print(f"  Total candles saved: {total_saved}")
        if failed:
            print(f"  Failed: {len(failed)} ({failed[:10]}...)")

    # Step 3: Verify
    print(f"\n[3/3] Verifying database...")
    conn = sqlite3.connect(DB_PATH)
    stats = conn.execute("""
        SELECT ticker, COUNT(*) as cnt, MIN(date) as min_dt, MAX(date) as max_dt
        FROM candles
        WHERE date >= ?
        GROUP BY ticker
        HAVING cnt >= 20
        ORDER BY cnt DESC
    """, (START_DATE,)).fetchall()
    conn.close()

    print(f"  Tickers with 20+ bars in period: {len(stats)}")
    print(f"\n  TOP-20 by bar count:")
    for t, cnt, mn, mx in stats[:20]:
        print(f"    {t:10s} | {cnt:4d} bars | {mn} to {mx}")

    print(f"\n  TOTAL tickers available: {len(stats)}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
