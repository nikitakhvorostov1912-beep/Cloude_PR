"""Load HOURLY (H1) candles for ALL MOEX tickers + futures + IMOEX.

~500 H1 bars per ticker per 3 months.
Total: ~260 tickers * 500 = ~130,000 candles.

Usage:
    python scripts/load_h1_universe.py
"""
import asyncio
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import aiohttp

ISS = "https://iss.moex.com/iss"
DB = Path("data/trading.db")
START = "2025-12-18"
END = "2026-03-18"


def init_h1_table():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_h1 (
            ticker TEXT NOT NULL,
            datetime TEXT NOT NULL,
            date TEXT NOT NULL,
            hour INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL DEFAULT 0,
            value REAL DEFAULT 0,
            source TEXT DEFAULT 'moex_iss',
            PRIMARY KEY (ticker, datetime)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_h1_ticker_date ON candles_h1(ticker, date)")
    conn.commit()
    conn.close()


async def fetch_h1_candles(session, ticker, board, engine, market):
    """Fetch H1 candles for a ticker from MOEX ISS."""
    all_candles = []
    cursor = 0

    while True:
        url = (
            f"{ISS}/engines/{engine}/markets/{market}/boards/{board}/securities/{ticker}/candles.json"
            f"?from={START}&till={END}&interval=60&iss.meta=off&start={cursor}"
        )
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    break
                data = await resp.json()
        except Exception:
            break

        rows = data.get("candles", {}).get("data", [])
        cols = data.get("candles", {}).get("columns", [])
        if not rows:
            break

        ci = {c: i for i, c in enumerate(cols)}

        for r in rows:
            try:
                dt_str = str(r[ci.get("begin", 0)] or "")
                if len(dt_str) < 10:
                    continue
                dt_date = dt_str[:10]
                dt_hour = int(dt_str[11:13]) if len(dt_str) > 12 else 0
                o = float(r[ci.get("open", 1)] or 0)
                c = float(r[ci.get("close", 2)] or 0)
                h = float(r[ci.get("high", 3)] or 0)
                l = float(r[ci.get("low", 4)] or 0)
                v = float(r[ci.get("volume", 5)] or 0)
                val = float(r[ci.get("value", 6)] or 0)
                if c > 0:
                    all_candles.append((ticker, dt_str[:16], dt_date, dt_hour, o, h, l, c, v, val))
            except (ValueError, TypeError, IndexError):
                continue

        cursor += len(rows)
        if len(rows) < 500:
            break

    return all_candles


def save_batch(candles):
    if not candles:
        return 0
    conn = sqlite3.connect(DB)
    saved = 0
    for c in candles:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO candles_h1
                   (ticker, datetime, date, hour, open, high, low, close, volume, value, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'moex_iss')""",
                c,
            )
            saved += 1
        except sqlite3.Error:
            continue
    conn.commit()
    conn.close()
    return saved


async def main():
    print("=" * 70)
    print(f"  Loading H1 candles for ALL MOEX tickers: {START} to {END}")
    print("=" * 70)

    init_h1_table()

    async with aiohttp.ClientSession() as session:
        # === 1. Get all TQBR tickers ===
        print("\n[1/4] Fetching ticker list...")
        url = f"{ISS}/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off"
        async with session.get(url) as resp:
            data = await resp.json()
        sec_data = data.get("securities", {}).get("data", [])
        sec_cols = data.get("securities", {}).get("columns", [])
        si = {c: i for i, c in enumerate(sec_cols)}
        tickers = [str(r[si.get("SECID", 0)]) for r in sec_data if r[si.get("SECID", 0)]]
        print(f"  TQBR tickers: {len(tickers)}")

        # === 2. Load H1 for all stocks ===
        print(f"\n[2/4] Loading H1 candles for {len(tickers)} stocks...")
        total_saved = 0
        loaded_count = 0

        batch_size = 10
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            tasks = [fetch_h1_candles(session, t, "TQBR", "stock", "shares") for t in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for ticker, result in zip(batch, results):
                if isinstance(result, Exception) or not result:
                    continue
                saved = save_batch(result)
                total_saved += saved
                loaded_count += 1
                sys.stdout.write(f"\r  {loaded_count}/{len(tickers)} tickers | {total_saved} H1 candles")
                sys.stdout.flush()

            await asyncio.sleep(0.2)

        print(f"\n  Stocks loaded: {loaded_count} | H1 candles: {total_saved}")

        # === 3. IMOEX index H1 ===
        print("\n[3/4] Loading IMOEX + USDRUB H1...")
        for idx_ticker, board, engine, market in [
            ("IMOEX", "SNDX", "stock", "index"),
        ]:
            candles = await fetch_h1_candles(session, idx_ticker, board, engine, market)
            if candles:
                n = save_batch(candles)
                total_saved += n
                print(f"  {idx_ticker}: {n} H1 candles")

        # === 4. Futures H1 ===
        print("\n[4/4] Loading futures H1...")
        futures_tickers = ["SiH6", "SiM6", "SiZ5", "BRJ6", "BRK6", "BRG6", "BRF6", "BRM6"]
        for ft in futures_tickers:
            candles = await fetch_h1_candles(session, ft, "RFUD", "futures", "forts")
            if candles:
                n = save_batch([
                    (f"FUT_{ft}", c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9])
                    for c in candles
                ])
                total_saved += n
                if n > 0:
                    print(f"  FUT_{ft}: {n} H1 candles")

    # === Verify ===
    print(f"\n{'='*70}")
    print("  VERIFICATION")
    print(f"{'='*70}")
    conn = sqlite3.connect(DB)

    total_h1 = conn.execute("SELECT COUNT(*) FROM candles_h1").fetchone()[0]
    tickers_h1 = conn.execute("SELECT COUNT(DISTINCT ticker) FROM candles_h1").fetchone()[0]
    print(f"  Total H1 candles: {total_h1}")
    print(f"  Total tickers: {tickers_h1}")

    # Per-ticker stats
    stats = conn.execute("""
        SELECT ticker, COUNT(*) as cnt, MIN(datetime) as mn, MAX(datetime) as mx
        FROM candles_h1
        GROUP BY ticker
        ORDER BY cnt DESC
        LIMIT 20
    """).fetchall()
    print(f"\n  TOP-20 by bar count:")
    for t, cnt, mn, mx in stats:
        print(f"    {t:12s}: {cnt:5d} H1 bars | {mn} to {mx}")

    # Coverage by date
    dates = conn.execute("""
        SELECT date, COUNT(DISTINCT ticker) as tickers, COUNT(*) as bars
        FROM candles_h1
        GROUP BY date
        ORDER BY date
        LIMIT 5
    """).fetchall()
    print(f"\n  First 5 dates:")
    for d, tc, bars in dates:
        print(f"    {d}: {tc} tickers, {bars} bars")

    last_dates = conn.execute("""
        SELECT date, COUNT(DISTINCT ticker) as tickers, COUNT(*) as bars
        FROM candles_h1
        GROUP BY date
        ORDER BY date DESC
        LIMIT 5
    """).fetchall()
    print(f"\n  Last 5 dates:")
    for d, tc, bars in last_dates:
        print(f"    {d}: {tc} tickers, {bars} bars")

    conn.close()
    print(f"\n{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
