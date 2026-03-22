"""Full system backtest: MTF + News + Futures + MiMo + Pairs Trading.

Usage:
    python scripts/backtest_full_system.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os

from dotenv import load_dotenv

load_dotenv()

import polars as pl
import structlog

logger = structlog.get_logger(__name__)

USE_LLM = False  # set in main() after checking llm_client

# ═══════════════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════════════

START_DATE = date(2026, 2, 18)
END_DATE = date(2026, 3, 18)
CAPITAL = 1_000_000.0
MAX_POSITIONS = 7
POSITION_SIZE_PCT = 0.12
STOP_LOSS_ATR = 2.5
TAKE_PROFIT_ATR = 5.0
COMMISSION_PCT = 0.0001
MIN_PRE_SCORE = 45.0
MAX_LLM_PER_DAY = 5

TICKERS_EQUITY = [
    "SBER", "GAZP", "LKOH", "ROSN", "GMKN", "NVTK", "VTBR",
    "YDEX", "MGNT", "TATN", "MTSS", "PLZL", "CHMF", "PHOR",
    "MOEX", "ALRS", "AFLT", "SNGS", "PIKK", "OZON",
]
TICKERS_FUTURES = ["SiH6", "BRJ6"]
ALL_TICKERS = TICKERS_EQUITY + TICKERS_FUTURES + ["IMOEX"]


# ═══════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════

@dataclass
class Position:
    ticker: str
    side: str
    entry_price: float
    quantity: float
    entry_date: date
    stop_loss: float
    take_profit: float
    atr: float
    reason: str = ""
    llm_used: bool = False


@dataclass
class Trade:
    ticker: str
    side: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    commission: float
    pre_score: float = 0.0
    mtf_score: float = 0.0
    news_sentiment: float = 0.0
    llm_used: bool = False


@dataclass
class DayResult:
    date: date
    equity: float
    cash: float
    positions_value: float
    trades_today: list[Trade]
    signals_generated: int
    llm_calls: int
    news_count: int
    regime: str
    mtf_agreement: float


# ═══════════════════════════════════════════════════
# ЗАГРУЗКА ДАННЫХ
# ═══════════════════════════════════════════════════

async def load_all_history() -> dict[str, list[dict]]:
    """Load history from SQLite DB + parquet fallback."""
    import sqlite3

    db_path = Path("data/trading.db")
    data: dict[str, list[dict]] = {}

    if db_path.exists():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ticker, dt, open, high, low, close, volume FROM candles ORDER BY dt ASC"
        ).fetchall()
        conn.close()
        for r in rows:
            t = r["ticker"]
            data.setdefault(t, []).append(dict(r))

    # Parquet fallback
    history_dir = Path("data/history")
    if history_dir.exists():
        for pq in history_dir.glob("*.parquet"):
            ticker = pq.stem
            if ticker not in data or len(data.get(ticker, [])) < 50:
                try:
                    df = pl.read_parquet(pq)
                    rows_list = []
                    for row in df.iter_rows(named=True):
                        rows_list.append({
                            "ticker": ticker,
                            "dt": str(row.get("timestamp", row.get("date", ""))),
                            "open": row.get("open", 0),
                            "high": row.get("high", 0),
                            "low": row.get("low", 0),
                            "close": row.get("close", 0),
                            "volume": row.get("volume", 0),
                        })
                    if rows_list:
                        data[ticker] = rows_list
                except Exception:
                    pass

    return data


def get_bars_until(all_bars: list[dict], until_date: date, lookback: int = 250) -> list[dict]:
    """Return last `lookback` bars up to `until_date` inclusive."""
    filtered = []
    for b in all_bars:
        dt_raw = b.get("dt") or b.get("timestamp") or b.get("date") or ""
        try:
            if isinstance(dt_raw, str):
                bar_date = date.fromisoformat(dt_raw[:10])
            elif isinstance(dt_raw, datetime):
                bar_date = dt_raw.date()
            elif isinstance(dt_raw, date):
                bar_date = dt_raw
            else:
                continue
            if bar_date <= until_date:
                filtered.append({**b, "_date": bar_date})
        except Exception:
            continue
    filtered.sort(key=lambda x: x["_date"])
    return filtered[-lookback:]


# ═══════════════════════════════════════════════════
# АНАЛИЗ ДНЯ
# ═══════════════════════════════════════════════════

def _bars_to_df(bars: list[dict]) -> pl.DataFrame:
    """Convert bar dicts to Polars DataFrame for features calculation."""
    return pl.DataFrame({
        "date": [b.get("dt", b.get("_date", "")) for b in bars],
        "open": [float(b.get("open", 0)) for b in bars],
        "high": [float(b.get("high", 0)) for b in bars],
        "low": [float(b.get("low", 0)) for b in bars],
        "close": [float(b.get("close", 0)) for b in bars],
        "volume": [float(b.get("volume", 0)) for b in bars],
    })


def analyze_day_fast(
    sim_date: date,
    precomputed: dict[str, dict[date, dict]],
    precomputed_mtf: dict[str, dict[date, Any]],
    ml_models: dict,
    macro_cache: dict,
    news_cache: list[dict],
    imoex_regime_cache: dict[date, str],
) -> dict[str, Any]:
    """Fast day analysis using precomputed features (no recalculation)."""
    from src.analysis.scoring import calculate_pre_score
    from src.analysis.sentiment import aggregate_daily_sentiment

    regime = imoex_regime_cache.get(sim_date, "weak_trend")

    ticker_scores: dict[str, float] = {}
    ticker_features: dict[str, dict] = {}
    ticker_mtf: dict[str, Any] = {}

    for ticker in TICKERS_EQUITY:
        ticker_days = precomputed.get(ticker, {})
        available = [d for d in ticker_days if d <= sim_date]
        if not available:
            continue
        feat = dict(ticker_days[max(available)])

        # Sentiment
        ticker_news = [n for n in news_cache if ticker in n.get("tickers", [])]
        sentiment = 0.0
        if ticker_news:
            sentiment = aggregate_daily_sentiment(
                [{"sentiment": n.get("sentiment", 0)} for n in ticker_news]
            )
        feat["sentiment"] = sentiment

        # Pre-score
        try:
            pre_score, _ = calculate_pre_score(
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
                sentiment_score=sentiment,
                direction="long",
            )
        except Exception:
            pre_score = 40.0

        # ML boost
        ml = ml_models.get(ticker)
        if ml and ml.is_trained:
            try:
                ml_score = ml.predict_score(feat)
                feat["ml_score"] = ml_score
                if ml_score > 60:
                    pre_score = min(100, pre_score + (ml_score - 60) * 0.3)
            except Exception:
                pass

        # MTF from precomputed cache
        mtf_days = precomputed_mtf.get(ticker, {})
        mtf_avail = [d for d in mtf_days if d <= sim_date]
        if mtf_avail:
            mtf_result = mtf_days[max(mtf_avail)]
            ticker_mtf[ticker] = mtf_result
            if mtf_result.tradeable and mtf_result.confidence_boost > 0:
                pre_score = min(100, pre_score + mtf_result.confidence_boost * 20)

        ticker_scores[ticker] = pre_score
        ticker_features[ticker] = feat

    return {
        "regime": regime,
        "scores": ticker_scores,
        "features": ticker_features,
        "mtf": ticker_mtf,
    }


# ═══════════════════════════════════════════════════
# ГЕНЕРАЦИЯ СИГНАЛОВ
# ═══════════════════════════════════════════════════

async def generate_signals_for_day(
    sim_date: date,
    analysis: dict,
    all_data: dict,
    news_cache: list[dict],
    llm_calls_today: int,
) -> list[dict]:
    """Generate trading signals for a day."""
    from src.strategy.prompts import build_market_context

    scores = analysis["scores"]
    features = analysis["features"]
    mtf = analysis["mtf"]
    regime = analysis["regime"]

    # Universe ranking — composite score sort
    try:
        from src.strategy.universe_selector import rank_universe, select_top_n
        tickers_data = []
        for t, s in scores.items():
            f = features.get(t, {})
            tickers_data.append({
                "ticker": t,
                "sector": "banks" if t in ("SBER", "VTBR") else "oil_gas" if t in ("GAZP", "LKOH", "ROSN", "NVTK", "TATN") else "other",
                "close": f.get("close", 0),
                "ml_score": f.get("ml_score", 50),
                "rsi": f.get("rsi_14", 50),
                "returns_1m": f.get("returns_1m", 0),
                "returns_3m": f.get("returns_3m", 0),
                "returns_20d": f.get("returns_20d", 0),
                "imoex_return_20d": 0.0,
                "volume_ratio": f.get("volume_ratio_20", 1),
            })
        if tickers_data:
            macro_delta = {"brent_delta_pct": 0, "key_rate_delta": 0, "usd_rub_delta_pct": 0}
            ranked = rank_universe(tickers_data, macro_delta)
            top_tickers = [r.ticker for r in ranked[:10]]
            candidates = [(t, s) for t, s in scores.items()
                          if t in top_tickers and s >= MIN_PRE_SCORE]
        else:
            candidates = [(t, s) for t, s in scores.items() if s >= MIN_PRE_SCORE]
    except Exception as e:
        logger.debug("universe_ranking_fallback", error=str(e))
        candidates = [(t, s) for t, s in scores.items() if s >= MIN_PRE_SCORE]

    candidates.sort(key=lambda x: x[1], reverse=True)

    signals: list[dict] = []

    # --- LLM cache init (once) ---
    LLM_CACHE_FILE = Path("data/backtest_llm_cache.json")
    if not hasattr(generate_signals_for_day, "_llm_cache"):
        generate_signals_for_day._llm_cache = {}
        if LLM_CACHE_FILE.exists():
            try:
                generate_signals_for_day._llm_cache = json.loads(
                    LLM_CACHE_FILE.read_text(encoding="utf-8")
                )
            except Exception:
                pass
    llm_signal_cache = generate_signals_for_day._llm_cache

    # --- Parallel LLM helper ---
    async def _get_llm_signal(
        ticker: str,
        pre_score: float,
        feat: dict,
        regime: str,
        ticker_news: list[dict],
        sim_date: date,
        llm_signal_cache: dict,
    ) -> tuple[str, float, str, float, bool]:
        cache_key = f"{ticker}_{sim_date.isoformat()}"
        if cache_key in llm_signal_cache:
            cached = llm_signal_cache[cache_key]
            return (
                ticker, pre_score,
                cached.get("action", "hold"),
                cached.get("confidence", 0.0),
                True,
            )
        if not USE_LLM:
            return ticker, pre_score, "hold", 0.0, False
        try:
            from src.strategy.claude_engine import get_trading_signal
            from src.models.signal import Action

            context = build_market_context(
                ticker=ticker, regime=regime, features=feat,
                sentiment=feat.get("sentiment", 0),
                portfolio={}, macro={"key_rate": 16.0, "usd_rub": 82.4},
                news=ticker_news,
            )
            mtf_result = mtf.get(ticker)
            if mtf_result:
                context += (
                    f"\n\nMTF: score={mtf_result.mtf_score:+.3f} "
                    f"dominant={mtf_result.dominant_signal.value} "
                    f"tradeable={mtf_result.tradeable}"
                )
            sig = await get_trading_signal(ticker, context)
            action = "hold"
            confidence = 0.0
            if sig and sig.action != Action.HOLD:
                action = sig.action.value
                confidence = sig.confidence
            llm_signal_cache[cache_key] = {
                "action": action, "confidence": confidence,
            }
            return ticker, pre_score, action, confidence, True
        except Exception as e:
            logger.warning("llm_parallel_failed", ticker=ticker, error=str(e))
            return ticker, pre_score, "hold", 0.0, False

    # --- Launch all candidates in parallel ---
    tasks = [
        _get_llm_signal(
            t, s, features.get(t, {}), regime,
            [n for n in news_cache if t in n.get("tickers", [])],
            sim_date, llm_signal_cache,
        )
        for t, s in candidates[:MAX_LLM_PER_DAY]
    ]
    llm_results = await asyncio.gather(*tasks)

    # --- Process results ---
    for ticker, pre_score, action, confidence, llm_used_flag in llm_results:
        # Fallback: technical signal without LLM
        if action == "hold" and not llm_used_flag:
            feat = features.get(ticker, {})
            ema20 = feat.get("ema_20", 0)
            ema50 = feat.get("ema_50", 0)
            rsi = feat.get("rsi_14", 50)
            adx = feat.get("adx", 20)
            if ema20 > ema50 and 40 <= rsi <= 65 and adx > 22:
                action = "buy"
                confidence = min(0.75, pre_score / 100)

        if action in ("buy", "sell") and confidence >= 0.40:
            feat = features.get(ticker, {})
            close = feat.get("close", 0)
            atr = feat.get("atr_14", close * 0.02)
            if close <= 0:
                continue
            mtf_result = mtf.get(ticker)
            signals.append({
                "ticker": ticker,
                "action": action,
                "confidence": confidence,
                "entry_price": close,
                "stop_loss": close - STOP_LOSS_ATR * atr if action == "buy"
                else close + STOP_LOSS_ATR * atr,
                "take_profit": close + TAKE_PROFIT_ATR * atr if action == "buy"
                else close - TAKE_PROFIT_ATR * atr,
                "atr": atr,
                "pre_score": pre_score,
                "mtf_score": mtf_result.mtf_score if mtf_result else 0.0,
                "news_sentiment": feat.get("sentiment", 0),
                "llm_used": llm_used_flag,
                "reason": f"LLM conf={confidence:.2f}",
            })

    # --- Save LLM cache after day ---
    try:
        LLM_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LLM_CACHE_FILE.write_text(json.dumps(llm_signal_cache, indent=2))
    except Exception:
        pass

    # Pairs trading
    try:
        from src.strategy.pairs_trading import generate_pairs_signals

        candles_cache = {}
        for t in ["SBER", "VTBR", "LKOH", "ROSN"]:
            bars = get_bars_until(all_data.get(t, []), sim_date)
            if bars:
                candles_cache[t] = bars

        pair_sigs = generate_pairs_signals(candles_cache, sim_date)
        for ps in pair_sigs:
            for pair_t, side in [(ps.long_ticker, "buy"), (ps.short_ticker, "sell")]:
                close = features.get(pair_t, {}).get("close", 0)
                if close > 0:
                    signals.append({
                        "ticker": pair_t,
                        "action": side,
                        "confidence": ps.confidence,
                        "entry_price": close,
                        "stop_loss": close * (0.96 if side == "buy" else 1.04),
                        "take_profit": close * (1.04 if side == "buy" else 0.96),
                        "atr": close * 0.015,
                        "pre_score": 50.0,
                        "mtf_score": 0.0,
                        "news_sentiment": 0.0,
                        "llm_used": False,
                        "reason": f"pairs z={ps.zscore:.2f}",
                    })
    except Exception as e:
        logger.debug("pairs_failed", error=str(e))

    return signals


# ═══════════════════════════════════════════════════
# СИМУЛЯЦИЯ ПОРТФЕЛЯ
# ═══════════════════════════════════════════════════

def update_positions(
    positions: list[Position],
    current_prices: dict[str, float],
    sim_date: date,
) -> tuple[list[Position], list[Trade]]:
    """Check stop-losses and take-profits."""
    remaining: list[Position] = []
    closed_trades: list[Trade] = []

    for pos in positions:
        price = current_prices.get(pos.ticker)
        if not price:
            remaining.append(pos)
            continue

        exit_reason = None
        exit_price = price

        if pos.side == "long":
            if price <= pos.stop_loss:
                exit_reason = "stop_loss"
                exit_price = pos.stop_loss
            elif price >= pos.take_profit:
                exit_reason = "take_profit"
                exit_price = pos.take_profit
        else:
            if price >= pos.stop_loss:
                exit_reason = "stop_loss"
                exit_price = pos.stop_loss
            elif price <= pos.take_profit:
                exit_reason = "take_profit"
                exit_price = pos.take_profit

        if exit_reason:
            pnl = ((exit_price - pos.entry_price) * pos.quantity
                   if pos.side == "long"
                   else (pos.entry_price - exit_price) * pos.quantity)
            commission = exit_price * pos.quantity * COMMISSION_PCT
            pnl -= commission
            pnl_pct = pnl / (pos.entry_price * pos.quantity) if pos.entry_price * pos.quantity > 0 else 0

            closed_trades.append(Trade(
                ticker=pos.ticker, side=pos.side,
                entry_date=pos.entry_date, exit_date=sim_date,
                entry_price=pos.entry_price, exit_price=exit_price,
                quantity=pos.quantity, pnl=pnl, pnl_pct=pnl_pct,
                exit_reason=exit_reason, commission=commission,
                llm_used=pos.llm_used,
            ))
        else:
            remaining.append(pos)

    return remaining, closed_trades


def open_positions(
    signals: list[dict],
    positions: list[Position],
    cash: float,
    sim_date: date,
) -> tuple[list[Position], float]:
    """Open new positions from signals."""
    new_positions = list(positions)
    current_tickers = {p.ticker for p in new_positions}

    for sig in signals:
        ticker = sig["ticker"]
        if ticker in current_tickers:
            continue
        if len(new_positions) >= MAX_POSITIONS:
            break

        position_value = min(CAPITAL * POSITION_SIZE_PCT, cash * 0.95)
        if position_value < 1000:
            break

        entry_price = sig["entry_price"]
        if entry_price <= 0:
            continue

        quantity = position_value / entry_price
        commission = entry_price * quantity * COMMISSION_PCT
        total_cost = entry_price * quantity + commission

        if total_cost > cash:
            continue

        new_positions.append(Position(
            ticker=ticker,
            side="long" if sig["action"] == "buy" else "short",
            entry_price=entry_price,
            quantity=quantity,
            entry_date=sim_date,
            stop_loss=sig["stop_loss"],
            take_profit=sig["take_profit"],
            atr=sig["atr"],
            reason=sig.get("reason", ""),
            llm_used=sig.get("llm_used", False),
        ))
        current_tickers.add(ticker)
        cash -= total_cost

    return new_positions, cash


# ═══════════════════════════════════════════════════
# ОТЧЁТ
# ═══════════════════════════════════════════════════

def generate_report(
    day_results: list[DayResult],
    all_trades: list[Trade],
    start_capital: float,
) -> str:
    """Generate final backtest report."""
    if not day_results:
        return "Нет данных для отчёта"

    final_equity = day_results[-1].equity
    total_return = (final_equity - start_capital) / start_capital * 100
    max_dd = 0.0
    peak = start_capital
    for d in day_results:
        if d.equity > peak:
            peak = d.equity
        dd = (peak - d.equity) / peak * 100
        max_dd = max(max_dd, dd)

    wins = [t for t in all_trades if t.pnl > 0]
    losses = [t for t in all_trades if t.pnl <= 0]
    win_rate = len(wins) / len(all_trades) * 100 if all_trades else 0
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_win = gross_profit / len(wins) if wins else 0
    avg_loss = gross_loss / len(losses) if losses else 0

    llm_trades = [t for t in all_trades if t.llm_used]
    tech_trades = [t for t in all_trades if not t.llm_used]

    by_exit: dict[str, int] = {}
    for t in all_trades:
        by_exit[t.exit_reason] = by_exit.get(t.exit_reason, 0) + 1

    lines = [
        "=" * 60,
        "  ПОЛНЫЙ БЭКТЕСТ MOEX Trading System",
        f"  {START_DATE} -> {END_DATE}",
        "=" * 60,
        f"  Начальный капитал:  {start_capital:>12,.0f} RUB",
        f"  Финальный капитал:  {final_equity:>12,.0f} RUB",
        f"  Доходность:         {total_return:>+11.2f}%",
        f"  Макс. просадка:     {max_dd:>11.2f}%",
        "",
        f"  Торговых дней:      {len(day_results):>5}",
        f"  Всего сделок:       {len(all_trades):>5}",
        f"  Прибыльных:         {len(wins):>5} ({win_rate:.0f}%)",
        f"  Убыточных:          {len(losses):>5} ({100 - win_rate:.0f}%)",
        f"  Profit Factor:      {pf:>11.2f}",
        f"  Средний выигрыш:    {avg_win:>+10,.0f} RUB",
        f"  Средний проигрыш:   {-avg_loss:>+10,.0f} RUB",
        "",
        f"  LLM сигналов:       {len(llm_trades):>5}",
        f"  Тех. сигналов:      {len(tech_trades):>5}",
        "",
        "  Выходы по причине:",
    ]
    for reason, count in sorted(by_exit.items()):
        lines.append(f"    {reason:<20} {count:>3}")

    lines += ["", "  Топ-5 сделок:"]
    for t in sorted(all_trades, key=lambda x: x.pnl, reverse=True)[:5]:
        lines.append(
            f"    {t.ticker:6} {t.side:5} "
            f"{t.entry_date}->{t.exit_date} "
            f"PnL={t.pnl:>+8,.0f}RUB ({t.pnl_pct:>+.1%}) [{t.exit_reason}]"
        )

    lines += ["", "  Худшие 5 сделок:"]
    for t in sorted(all_trades, key=lambda x: x.pnl)[:5]:
        lines.append(
            f"    {t.ticker:6} {t.side:5} "
            f"{t.entry_date}->{t.exit_date} "
            f"PnL={t.pnl:>+8,.0f}RUB ({t.pnl_pct:>+.1%}) [{t.exit_reason}]"
        )

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════
# ГЛАВНЫЙ ЦИКЛ
# ═══════════════════════════════════════════════════

async def main():
    import time as _time
    t0 = _time.time()

    print("Загружаю данные...")
    all_data = await load_all_history()
    print(f"Тикеров: {len(all_data)}")

    # Load news (skip in tech-only mode to avoid LLM calls)
    news_cache: list[dict] = []
    if os.environ.get("BACKTEST_NEWS", "0") == "1":
        print("Загружаю новости...")
        try:
            from src.strategy.news_reactor import NewsReactor, NewsImpact
            reactor = NewsReactor(min_impact=NewsImpact.MEDIUM)
            signals = await reactor.check_feeds()
            news_cache = [{
                "title": s.headline,
                "sentiment": s.confidence if s.direction == "bullish" else -s.confidence,
                "impact": s.impact.value,
                "direction": s.direction,
                "tickers": [s.ticker],
            } for s in signals]
            print(f"Новостей: {len(news_cache)}")
        except Exception as e:
            print(f"Новости недоступны: {e}")
    else:
        print("Новости: пропущены (BACKTEST_NEWS=1 для включения)")

    macro_cache = {
        "key_rate": 16.0, "brent": 75.0, "usd_rub": 82.4,
        "imoex_above_sma200": True,
    }

    # Check LLM
    global USE_LLM
    from src.core.llm_client import get_llm_client
    llm = get_llm_client()
    USE_LLM = True  # LLM backtest with new prompts
    print(f"LLM: {'ON (' + llm._model + ')' if USE_LLM else 'OFF (tech fallback)'}")

    # LLM cache
    llm_signal_cache: dict[str, dict] = {}
    LLM_CACHE_FILE = Path("data/backtest_llm_cache.json")
    if LLM_CACHE_FILE.exists():
        try:
            llm_signal_cache = json.loads(LLM_CACHE_FILE.read_text())
            print(f"LLM кэш: {len(llm_signal_cache)} записей")
        except Exception:
            pass

    def save_llm_cache():
        try:
            LLM_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            LLM_CACHE_FILE.write_text(json.dumps(llm_signal_cache))
        except Exception:
            pass

    # ═══ PRECOMPUTE: features for ALL tickers ONCE ═══
    print("Предрассчитываю features...")
    from src.analysis.features import calculate_all_features
    from src.analysis.mtf import TimeFrame, analyze_single_tf, TFSignal

    precomputed: dict[str, dict[date, dict]] = {}
    precomputed_mtf: dict[str, dict[date, Any]] = {}

    for ticker in TICKERS_EQUITY + ["IMOEX"]:
        bars = all_data.get(ticker, [])
        if len(bars) < 30:
            continue
        try:
            df = _bars_to_df(bars)
            df = calculate_all_features(df)

            ticker_days: dict[date, dict] = {}
            for row in df.iter_rows(named=True):
                dt_raw = row.get("date", "")
                try:
                    if isinstance(dt_raw, str) and len(dt_raw) >= 10:
                        bar_date = date.fromisoformat(dt_raw[:10])
                    elif isinstance(dt_raw, datetime):
                        bar_date = dt_raw.date()
                    elif isinstance(dt_raw, date):
                        bar_date = dt_raw
                    else:
                        continue
                    ticker_days[bar_date] = {
                        k: float(v) if isinstance(v, (int, float)) else 0.0
                        for k, v in row.items()
                    }
                except Exception:
                    continue
            precomputed[ticker] = ticker_days
            print(f"  {ticker}: {len(ticker_days)} дней", end="")

            # MTF: compute once per bar (D1 only — fast)
            mtf_days: dict[date, Any] = {}
            sorted_dates = sorted(ticker_days.keys())
            for i, d in enumerate(sorted_dates):
                if i < 20:
                    continue
                window = [ticker_days[sorted_dates[j]] for j in range(max(0, i - 249), i + 1)]
                tf_result = analyze_single_tf(ticker, TimeFrame.D1, window)
                if tf_result:
                    # Minimal MTF result object
                    mtf_days[d] = type("MTF", (), {
                        "mtf_score": tf_result.composite_score,
                        "dominant_signal": tf_result.signal,
                        "tradeable": tf_result.signal in (
                            TFSignal.BULL, TFSignal.STRONG_BULL,
                            TFSignal.BEAR, TFSignal.STRONG_BEAR),
                        "confidence_boost": 0.08 if tf_result.signal in (
                            TFSignal.STRONG_BULL, TFSignal.STRONG_BEAR) else 0.0,
                        "analyses": {TimeFrame.D1: tf_result},
                    })()
            precomputed_mtf[ticker] = mtf_days
            print(f" mtf={len(mtf_days)}")
        except Exception as e:
            print(f"  {ticker}: FAILED ({e})")

    print(f"Предрассчитано: {len(precomputed)} тикеров")

    # ═══ IMOEX regime cache ═══
    imoex_regime_cache: dict[date, str] = {}
    for d, feat in precomputed.get("IMOEX", {}).items():
        adx = feat.get("adx", 20)
        if adx > 25:
            imoex_regime_cache[d] = "strong_trend"
        elif adx < 15:
            imoex_regime_cache[d] = "range"
        else:
            imoex_regime_cache[d] = "weak_trend"

    # ═══ ML: train once ═══
    print("Тренирую ML модели...")
    from src.ml.ensemble import MLEnsemble
    ml_models: dict[str, MLEnsemble] = {}
    for ticker in TICKERS_EQUITY:
        bars = all_data.get(ticker, [])
        if len(bars) < 100:
            continue
        try:
            ens = MLEnsemble()
            cut = int(len(bars) * 0.8)
            train_candles = [{"close": float(b.get("close", 0)), "dt": b.get("dt", "")}
                             for b in bars[:cut]]
            train_ta = [{k: float(v) if isinstance(v, (int, float)) else 0.0
                         for k, v in b.items() if k not in ("_date", "ticker")}
                        for b in bars[:cut]]
            if ens.train(train_candles, train_ta):
                ml_models[ticker] = ens
        except Exception:
            pass
    print(f"ML моделей: {len(ml_models)}")

    # ═══ Price index for fast lookup ═══
    print("Строю индекс цен...")
    price_index: dict[str, dict[date, float]] = {}
    for ticker in ALL_TICKERS:
        ticker_prices: dict[date, float] = {}
        for b in all_data.get(ticker, []):
            dt_raw = b.get("dt") or b.get("timestamp") or b.get("date") or ""
            try:
                if isinstance(dt_raw, str) and len(dt_raw) >= 10:
                    d = date.fromisoformat(dt_raw[:10])
                elif isinstance(dt_raw, datetime):
                    d = dt_raw.date()
                elif isinstance(dt_raw, date):
                    d = dt_raw
                else:
                    continue
                ticker_prices[d] = float(b.get("close", 0))
            except Exception:
                continue
        price_index[ticker] = ticker_prices

    def get_price(ticker: str, d: date) -> float:
        prices = price_index.get(ticker, {})
        if d in prices:
            return prices[d]
        avail = [dd for dd in prices if dd <= d]
        return prices[max(avail)] if avail else 0.0

    # ═══ Trading days ═══
    trading_days: list[date] = []
    d = START_DATE
    while d <= END_DATE:
        if d.weekday() < 5:
            trading_days.append(d)
        d += timedelta(days=1)

    setup_time = _time.time() - t0
    print(f"\nSetup: {setup_time:.1f}с")
    print(f"Торговых дней: {len(trading_days)}")
    print("Запускаю симуляцию...\n")

    # ═══ MAIN LOOP ═══
    t1 = _time.time()
    cash = CAPITAL
    positions: list[Position] = []
    all_trades: list[Trade] = []
    day_results: list[DayResult] = []
    llm_calls_total = 0

    for sim_date in trading_days:
        print(f"  {sim_date}...", end=" ", flush=True)

        # Current prices (fast lookup)
        current_prices = {t: get_price(t, sim_date) for t in ALL_TICKERS}

        # Check stops/takes
        positions, closed_today = update_positions(positions, current_prices, sim_date)
        all_trades.extend(closed_today)
        for t in closed_today:
            cash += t.entry_price * t.quantity + t.pnl

        # Analyze (FAST — uses precomputed)
        analysis = analyze_day_fast(
            sim_date, precomputed, precomputed_mtf,
            ml_models, macro_cache, news_cache, imoex_regime_cache,
        )

        # Generate signals
        sigs = await generate_signals_for_day(
            sim_date, analysis, all_data, news_cache, 0,
        )
        llm_calls_total += sum(1 for s in sigs if s.get("llm_used"))

        # Open positions
        positions, cash = open_positions(sigs, positions, cash, sim_date)

        # Equity
        positions_value = sum(
            current_prices.get(p.ticker, p.entry_price) * p.quantity
            for p in positions
        )
        equity = cash + positions_value
        mtf_vals = [getattr(r, "mtf_score", 0) for r in analysis["mtf"].values()]
        avg_mtf = sum(mtf_vals) / len(mtf_vals) if mtf_vals else 0

        day_results.append(DayResult(
            date=sim_date, equity=equity, cash=cash,
            positions_value=positions_value, trades_today=closed_today,
            signals_generated=len(sigs), llm_calls=0,
            news_count=len(news_cache), regime=analysis["regime"],
            mtf_agreement=avg_mtf,
        ))

        pnl_today = sum(t.pnl for t in closed_today)
        print(
            f"eq={equity:,.0f} pos={len(positions)} "
            f"tr={len(closed_today)} pnl={pnl_today:>+,.0f} "
            f"regime={analysis['regime']}"
        )

    # Close all remaining positions
    for pos in positions:
        price = current_prices.get(pos.ticker, pos.entry_price)
        pnl = ((price - pos.entry_price) * pos.quantity
               if pos.side == "long"
               else (pos.entry_price - price) * pos.quantity)
        commission = price * pos.quantity * COMMISSION_PCT
        pnl -= commission
        pnl_pct = pnl / (pos.entry_price * pos.quantity) if pos.entry_price * pos.quantity > 0 else 0
        all_trades.append(Trade(
            ticker=pos.ticker, side=pos.side,
            entry_date=pos.entry_date, exit_date=END_DATE,
            entry_price=pos.entry_price, exit_price=price,
            quantity=pos.quantity, pnl=pnl, pnl_pct=pnl_pct,
            exit_reason="eod", commission=commission,
            llm_used=pos.llm_used,
        ))

    report = generate_report(day_results, all_trades, CAPITAL)
    print("\n" + report)

    Path("FULL_BACKTEST_REPORT.md").write_text(report, encoding="utf-8")
    print(f"\nОтчёт: FULL_BACKTEST_REPORT.md")

    loop_time = _time.time() - t1
    total_time = _time.time() - t0
    print(f"\nSetup: {setup_time:.1f}с | Симуляция: {loop_time:.1f}с | Всего: {total_time:.1f}с")

    # Save JSON
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/full_backtest.json").write_text(json.dumps({
        "period": f"{START_DATE} -> {END_DATE}",
        "capital": CAPITAL,
        "final_equity": round(day_results[-1].equity, 2) if day_results else CAPITAL,
        "trades": len(all_trades),
        "llm_calls": llm_calls_total,
        "setup_seconds": round(setup_time, 1),
        "loop_seconds": round(loop_time, 1),
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
