"""Pre-fetch LLM signals into cache for fast backtest replay.

Calls MiMo LLM for top-3 candidates per trading day and saves results
to data/backtest_llm_cache.json.  Subsequent backtest runs read from
cache instead of calling LLM again.

Usage:
    python scripts/prefetch_llm_signals.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import warnings
from datetime import date, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

import polars as pl

# ── Config ──────────────────────────────────────────

START_DATE = date(2026, 2, 18)
END_DATE = date(2026, 3, 18)

TICKERS = [
    "SBER", "GAZP", "LKOH", "ROSN", "GMKN", "NVTK", "VTBR",
    "YDEX", "MGNT", "TATN", "MTSS", "PLZL", "CHMF", "PHOR",
    "MOEX", "ALRS", "AFLT", "SNGS", "PIKK", "OZON",
]

TOP_PER_DAY = 3
LLM_CACHE_FILE = Path("data/backtest_llm_cache.json")


# ── Helpers ─────────────────────────────────────────

def _load_cache() -> dict:
    if LLM_CACHE_FILE.exists():
        try:
            return json.loads(LLM_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    LLM_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LLM_CACHE_FILE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Main ────────────────────────────────────────────

async def main() -> None:
    from src.core.llm_client import get_llm_client

    llm = get_llm_client()
    print(f"LLM: {'ON (' + llm._model + ')' if llm.is_available else 'OFF'}")
    if not llm.is_available:
        print("API ключ не найден. Установи XIAOMI_API_KEY в .env")
        return

    cache = _load_cache()
    print(f"Кэш: {len(cache)} записей")

    # ── Load data & precompute features ─────────────
    print("Загружаю данные...")
    import sqlite3
    from src.analysis.features import calculate_all_features

    db_path = Path("data/trading.db")
    all_bars: dict[str, list[dict]] = {}

    if db_path.exists():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute(
            "SELECT ticker, dt, open, high, low, close, volume "
            "FROM candles ORDER BY dt ASC"
        ).fetchall():
            all_bars.setdefault(row["ticker"], []).append(dict(row))
        conn.close()

    # Parquet fallback
    for pq in Path("data/history").glob("*.parquet"):
        t = pq.stem
        if t not in all_bars or len(all_bars[t]) < 50:
            try:
                df = pl.read_parquet(pq)
                all_bars[t] = [{
                    "ticker": t,
                    "dt": str(r.get("timestamp", r.get("date", ""))),
                    "open": r.get("open", 0), "high": r.get("high", 0),
                    "low": r.get("low", 0), "close": r.get("close", 0),
                    "volume": r.get("volume", 0),
                } for r in df.iter_rows(named=True)]
            except Exception:
                pass

    # Precompute features per ticker per date
    print("Предрассчитываю features...")
    precomputed: dict[str, dict[date, dict]] = {}
    for ticker in TICKERS:
        bars = all_bars.get(ticker, [])
        if len(bars) < 30:
            continue
        try:
            df = pl.DataFrame({
                "date": [b.get("dt", "") for b in bars],
                "open": [float(b.get("open", 0)) for b in bars],
                "high": [float(b.get("high", 0)) for b in bars],
                "low": [float(b.get("low", 0)) for b in bars],
                "close": [float(b.get("close", 0)) for b in bars],
                "volume": [float(b.get("volume", 0)) for b in bars],
            })
            df = calculate_all_features(df)
            ticker_days: dict[date, dict] = {}
            for row in df.iter_rows(named=True):
                dt_raw = row.get("date", "")
                try:
                    bar_date = date.fromisoformat(str(dt_raw)[:10])
                    ticker_days[bar_date] = {
                        k: float(v) if isinstance(v, (int, float)) else 0.0
                        for k, v in row.items()
                    }
                except Exception:
                    continue
            precomputed[ticker] = ticker_days
        except Exception:
            pass
    print(f"Тикеров: {len(precomputed)}")

    # ── Trading days ────────────────────────────────
    trading_days: list[date] = []
    d = START_DATE
    while d <= END_DATE:
        if d.weekday() < 5:
            trading_days.append(d)
        d += timedelta(days=1)
    print(f"Торговых дней: {len(trading_days)}\n")

    # ── Imports for signal generation ───────────────
    from src.analysis.scoring import calculate_pre_score
    from src.strategy.prompts import build_market_context
    from src.strategy.claude_engine import get_trading_signal
    from src.models.signal import Action

    total_new = 0
    total_skip = 0

    for sim_date in trading_days:
        # Pre-scores for this date
        scores: dict[str, float] = {}
        for ticker in TICKERS:
            days = precomputed.get(ticker, {})
            avail = [dd for dd in days if dd <= sim_date]
            if not avail:
                continue
            feat = days[max(avail)]
            try:
                ps, _ = calculate_pre_score(
                    adx=feat.get("adx", 20),
                    di_plus=feat.get("di_plus", 25),
                    di_minus=feat.get("di_minus", 20),
                    rsi=feat.get("rsi_14", 50),
                    macd_hist=feat.get("macd_histogram", 0),
                    close=feat.get("close", 1),
                    ema20=feat.get("ema_20", feat.get("close", 1)),
                    ema50=feat.get("ema_50", feat.get("close", 1)),
                    ema200=feat.get("ema_200", feat.get("close", 1)),
                    volume_ratio=feat.get("volume_ratio_20", 1),
                    obv_trend=feat.get("obv_trend", "flat"),
                    sentiment_score=0.0,
                    direction="long",
                )
                scores[ticker] = ps
            except Exception:
                pass

        # Top candidates
        candidates = sorted(
            [(t, s) for t, s in scores.items() if s >= 45],
            key=lambda x: x[1], reverse=True,
        )[:TOP_PER_DAY]

        print(f"{sim_date}: {len(candidates)} кандидатов", end="  ")

        for ticker, pre_score in candidates:
            cache_key = f"{ticker}_{sim_date.isoformat()}"

            if cache_key in cache:
                total_skip += 1
                c = cache[cache_key]
                print(f"[{ticker}={c['action']}(кэш)]", end=" ")
                continue

            # LLM call
            feat = precomputed.get(ticker, {})
            avail = [dd for dd in feat if dd <= sim_date]
            if not avail:
                continue
            day_feat = feat[max(avail)]

            try:
                context = build_market_context(
                    ticker=ticker,
                    regime="weak_trend",
                    features=day_feat,
                    sentiment=0.0,
                    portfolio={},
                    macro={"key_rate_pct": 16.0, "usd_rub": 82.4},
                )

                sig = await get_trading_signal(ticker, context)
                action = "hold"
                confidence = 0.0
                if sig and sig.action != Action.HOLD:
                    action = sig.action.value
                    confidence = sig.confidence

                cache[cache_key] = {
                    "action": action,
                    "confidence": round(confidence, 3),
                }
                total_new += 1
                print(f"[{ticker}={action}:{confidence:.2f}]", end=" ")

                _save_cache(cache)
                await asyncio.sleep(1)

            except Exception as e:
                print(f"[{ticker}=ERR:{e}]", end=" ")

        print()

    print(f"\nГотово: {total_new} новых, {total_skip} из кэша")
    print(f"Кэш: {len(cache)} записей -> {LLM_CACHE_FILE}")
    print("\nТеперь запускай:")
    print("  python scripts/backtest_full_system.py")


if __name__ == "__main__":
    asyncio.run(main())
