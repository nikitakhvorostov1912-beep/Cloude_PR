"""Backtest WITH real Claude API calls on historical MOEX data.

Compares three variants:
  A) Algorithm only (no Claude) -- baseline
  B) Algorithm + Claude Haiku  -- cheap LLM
  C) Algorithm + Claude Sonnet -- premium LLM (SBER only, 1 month, to show delta)

Claude responses are cached in SQLite so re-runs are free.

Usage:
    python -m scripts.backtest_with_claude
    python -m scripts.backtest_with_claude --skip-claude   # algo-only, no API calls
    python -m scripts.backtest_with_claude --use-cache     # only cached, no new calls
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic
import polars as pl
import structlog
from dotenv import load_dotenv

from src.analysis.features import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger,
    calculate_ema,
    calculate_macd,
    calculate_obv,
    calculate_rsi,
    calculate_stochastic,
    calculate_volume_ratio,
)
from src.analysis.regime import detect_regime_from_index
from src.analysis.scoring import calculate_pre_score
from src.models.market import MarketRegime, OHLCVBar
from src.strategy.prompts import SYSTEM_PROMPT, build_market_context

load_dotenv(override=True)

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
)
log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_PATH = str(Path("data/trading.db").resolve())
TICKERS = ["SBER", "LKOH", "GAZP"]
START_DATE = date(2024, 1, 1)
END_DATE = date(2026, 3, 18)
INITIAL_CAPITAL = 1_000_000.0
RISK_PER_TRADE = 0.015
MAX_POSITION_PCT = 0.15
ATR_MULT = 2.5
COMMISSION_RT = 0.001  # 0.1% round-trip (each side 0.05%)
PRE_SCORE_THRESHOLD = 30.0
CLAUDE_CONFIDENCE_THRESHOLD = 0.45
API_DELAY = 0.5  # seconds between Claude calls

MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-20250514"

# Token cost estimates (USD per 1M tokens)
COST_HAIKU_INPUT = 0.80
COST_HAIKU_OUTPUT = 4.00
COST_SONNET_INPUT = 3.00
COST_SONNET_OUTPUT = 15.00

BACKTEST_NOTE = (
    "\n\nПримечание: новостной sentiment недоступен для исторического бэктеста. "
    "Принимай решение на основе технических данных и макро."
)

# Tool definition (same as claude_engine.py)
SIGNAL_TOOL: dict = {
    "name": "submit_trading_signal",
    "description": "Submit trading signal based on market analysis",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["buy", "sell", "hold", "reduce"]},
            "direction": {"type": "string", "enum": ["long", "short"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit": {"type": "number"},
            "reasoning": {"type": "string"},
            "key_factors": {"type": "array", "items": {"type": "string"}},
            "risk_factors": {"type": "array", "items": {"type": "string"}},
            "strategy": {"type": "string"},
            "time_stop_days": {"type": "integer", "maximum": 30},
        },
        "required": ["action", "direction", "confidence", "reasoning"],
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Trade:
    ticker: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    lots: int
    pnl: float
    pnl_pct: float
    days_held: int
    exit_reason: str
    claude_action: str = ""
    claude_confidence: float = 0.0
    algo_action: str = ""
    claude_reasoning: str = ""


@dataclass
class TickerResult:
    ticker: str
    trades: list[Trade] = field(default_factory=list)
    final_equity: float = 0.0
    return_pct: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    equity_curve: list[float] = field(default_factory=list)


@dataclass
class BacktestVariantResult:
    name: str
    ticker_results: list[TickerResult] = field(default_factory=list)
    total_equity: float = 0.0
    total_return_pct: float = 0.0
    total_trades: int = 0
    total_wins: int = 0
    total_sharpe: float = 0.0
    total_max_dd: float = 0.0
    claude_calls: int = 0
    claude_input_tokens: int = 0
    claude_output_tokens: int = 0
    claude_cost_usd: float = 0.0
    divergent_decisions: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Claude Cache
# ---------------------------------------------------------------------------
CACHE_DDL = """
CREATE TABLE IF NOT EXISTS claude_cache (
    date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    model TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    response TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (date, ticker, model)
);
"""


def init_cache(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(CACHE_DDL)
    conn.commit()
    conn.close()


def get_cached_response(
    db_path: str, dt: date, ticker: str, model: str
) -> dict | None:
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT response, input_tokens, output_tokens FROM claude_cache "
        "WHERE date = ? AND ticker = ? AND model = ?",
        (dt.isoformat(), ticker, model),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "response": json.loads(row[0]),
        "input_tokens": row[1],
        "output_tokens": row[2],
    }


def save_cached_response(
    db_path: str,
    dt: date,
    ticker: str,
    model: str,
    input_hash: str,
    response: dict,
    input_tokens: int,
    output_tokens: int,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO claude_cache "
        "(date, ticker, model, input_hash, response, input_tokens, output_tokens) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            dt.isoformat(),
            ticker,
            model,
            input_hash,
            json.dumps(response, ensure_ascii=False),
            input_tokens,
            output_tokens,
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_candles_sync(db_path: str, ticker: str) -> list[OHLCVBar]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT ticker, date, open, high, low, close, volume, value "
        "FROM candles WHERE ticker = ? AND date >= ? AND date <= ? "
        "ORDER BY date ASC",
        (ticker, "2023-01-01", END_DATE.isoformat()),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        OHLCVBar(
            ticker=row["ticker"],
            dt=date.fromisoformat(row["date"]),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            value=row["value"],
        )
        for row in rows
    ]


def load_macro_usd_rub(db_path: str) -> dict[str, float]:
    """Load USDRUB candles as date->close lookup."""
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT date, close FROM candles WHERE ticker = 'USDRUB' ORDER BY date"
    )
    result = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return result


def candles_to_df(candles: list[OHLCVBar]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [c.dt for c in candles],
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
    ).sort("date")


def add_all_indicators(df: pl.DataFrame) -> pl.DataFrame:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    cols = []
    cols.append(calculate_ema(close, 20))
    cols.append(calculate_ema(close, 50))
    cols.append(calculate_ema(close, 200))
    cols.append(calculate_rsi(close, 14))

    macd_d = calculate_macd(close)
    cols.extend(macd_d.values())

    adx_d = calculate_adx(high, low, close, 14)
    cols.extend(adx_d.values())

    bb_d = calculate_bollinger(close, 20, 2.0)
    cols.extend(bb_d.values())

    cols.append(calculate_atr(high, low, close, 14))

    stoch_d = calculate_stochastic(high, low, close)
    cols.extend(stoch_d.values())

    cols.append(calculate_obv(close, volume))
    cols.append(calculate_volume_ratio(volume, 20))

    return df.with_columns(cols)


def get_row_features(row: dict) -> dict:
    """Extract feature dict from a DataFrame row."""
    return {
        "close": row.get("close", 0),
        "ema_20": row.get("ema_20"),
        "ema_50": row.get("ema_50"),
        "ema_200": row.get("ema_200"),
        "rsi_14": row.get("rsi_14"),
        "macd": row.get("macd"),
        "macd_signal": row.get("macd_signal"),
        "macd_histogram": row.get("macd_histogram"),
        "adx": row.get("adx"),
        "di_plus": row.get("di_plus"),
        "di_minus": row.get("di_minus"),
        "bb_upper": row.get("bb_upper"),
        "bb_lower": row.get("bb_lower"),
        "bb_pct_b": row.get("bb_pct_b"),
        "atr_14": row.get("atr_14"),
        "stoch_k": row.get("stoch_k"),
        "stoch_d": row.get("stoch_d"),
        "obv": row.get("obv"),
        "volume_ratio_20": row.get("volume_ratio_20"),
    }


def safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Algorithmic signal (no Claude)
# ---------------------------------------------------------------------------


def algo_signal(features: dict, strict: bool = True) -> str:
    """Algorithmic BUY/HOLD based on RSI + EMA + ADX.

    strict=True  -- original conservative signal (for algo-only variant)
    strict=False -- relaxed signal to generate more candidates for Claude
    """
    rsi = safe_float(features.get("rsi_14"))
    ema200 = safe_float(features.get("ema_200"))
    ema50 = safe_float(features.get("ema_50"))
    adx = safe_float(features.get("adx"))
    close = safe_float(features.get("close"))
    macd_hist = safe_float(features.get("macd_histogram"))

    if strict:
        # Original: RSI < 40, above EMA200, ADX > 20
        if rsi < 40 and close > ema200 and adx > 20:
            return "buy"
    else:
        # Relaxed: generate candidate signal for Claude to evaluate
        # BUY candidate if any of these conditions hold:
        # 1) Classic oversold bounce: RSI < 45 and above EMA200
        # 2) Trend following: price above EMA50, ADX > 20, MACD positive
        # 3) Mean reversion: RSI < 35 (deeply oversold)
        if rsi < 45 and close > ema200 and adx > 18:
            return "buy"
        if close > ema50 and adx > 22 and macd_hist > 0:
            return "buy"
        if rsi < 35:
            return "buy"
    return "hold"


def algo_exit_signal(features: dict, days_held: int) -> str | None:
    """Check exit conditions for algo-only variant."""
    rsi = safe_float(features.get("rsi_14"))
    ema50 = safe_float(features.get("ema_50"))
    adx = safe_float(features.get("adx"))
    close = safe_float(features.get("close"))

    if rsi > 70:
        return "rsi>70"
    if close < ema50 and adx > 25:
        return "ema_break"
    if days_held > 30:
        return "time_stop"
    return None


# ---------------------------------------------------------------------------
# Claude API call with caching
# ---------------------------------------------------------------------------


async def call_claude(
    dt: date,
    ticker: str,
    context_str: str,
    model: str,
    use_cache_only: bool = False,
) -> tuple[dict, int, int]:
    """Call Claude API or return cached response.

    Returns (parsed_response_dict, input_tokens, output_tokens).
    """
    cached = get_cached_response(DB_PATH, dt, ticker, model)
    if cached is not None:
        return cached["response"], cached["input_tokens"], cached["output_tokens"]

    if use_cache_only:
        return {"action": "hold", "direction": "long", "confidence": 0.0,
                "reasoning": "cache miss, skipped"}, 0, 0

    input_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]

    user_message = (
        f"Проанализируй тикер {ticker} и сформируй торговый сигнал.\n\n"
        f"Контекст рынка:\n{context_str}"
        f"{BACKTEST_NOTE}"
    )

    client = anthropic.AsyncAnthropic()
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0.1,
            system=SYSTEM_PROMPT,
            tools=[SIGNAL_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        log.error("claude_api_error", ticker=ticker, date=str(dt), error=str(exc))
        return {"action": "hold", "direction": "long", "confidence": 0.0,
                "reasoning": f"API error: {exc}"}, 0, 0

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    tool_block = next(
        (b for b in response.content if b.type == "tool_use"), None
    )

    if tool_block is None:
        parsed = {"action": "hold", "direction": "long", "confidence": 0.0,
                  "reasoning": "Claude did not use tool"}
    else:
        parsed = dict(tool_block.input)

    save_cached_response(DB_PATH, dt, ticker, model, input_hash,
                         parsed, input_tokens, output_tokens)

    await asyncio.sleep(API_DELAY)
    return parsed, input_tokens, output_tokens


# ---------------------------------------------------------------------------
# Generate decision points (Mondays)
# ---------------------------------------------------------------------------


def get_mondays(start: date, end: date) -> list[date]:
    """Return list of Mondays between start and end (inclusive)."""
    mondays = []
    d = start
    # Move to first Monday
    while d.weekday() != 0:
        d += timedelta(days=1)
    while d <= end:
        mondays.append(d)
        d += timedelta(days=7)
    return mondays


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_sharpe(equity_curve: list[float], rf_annual: float = 0.19) -> float:
    if len(equity_curve) < 10:
        return 0.0
    daily_rf = rf_annual / 252
    rets = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] > 0
    ]
    if not rets or len(rets) < 5:
        return 0.0
    excess = [r - daily_rf for r in rets]
    mean_ex = sum(excess) / len(excess)
    var = sum((r - mean_ex) ** 2 for r in excess) / max(len(excess) - 1, 1)
    std = math.sqrt(var)
    if std < 1e-10:
        return 0.0  # No meaningful variance (flat equity curve)
    return mean_ex / std * math.sqrt(252)


def compute_max_dd(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


# ---------------------------------------------------------------------------
# Run single-ticker backtest
# ---------------------------------------------------------------------------


async def run_ticker_backtest(
    ticker: str,
    df: pl.DataFrame,
    mondays: list[date],
    capital: float,
    use_claude: bool,
    model: str,
    use_cache_only: bool,
    usd_rub_lookup: dict[str, float],
    regime_candles: list[OHLCVBar],
) -> tuple[TickerResult, int, int, int, list[dict]]:
    """Run backtest for one ticker.

    Returns (TickerResult, claude_calls, input_tokens, output_tokens, divergent_list).
    """
    rows = df.to_dicts()
    date_to_idx: dict[date, int] = {}
    for i, r in enumerate(rows):
        date_to_idx[r["date"]] = i

    trades: list[Trade] = []
    position = None  # dict with entry info
    equity = capital
    peak_equity = capital
    equity_curve = [capital]
    claude_calls = 0
    total_input_tokens = 0
    total_output_tokens = 0
    divergent = []

    # Track which dates are mondays (decision points)
    monday_set = set(mondays)

    for i, row in enumerate(rows):
        dt = row["date"]
        if dt < START_DATE:
            continue

        close = row["close"]
        features = get_row_features(row)
        atr = safe_float(features.get("atr_14"))

        # Skip if indicators not ready
        if any(
            safe_float(features.get(k)) == 0.0
            for k in ["rsi_14", "ema_200", "adx", "atr_14"]
        ):
            equity_curve.append(equity)
            continue

        # --- EXIT check (every day) ---
        if position is not None:
            days_held = (dt - position["entry_date"]).days
            hit_stop = close <= position["stop_loss"]

            exit_reason = None
            exit_price = close

            if hit_stop:
                exit_reason = "stop_loss"
                exit_price = position["stop_loss"]
            else:
                exit_reason = algo_exit_signal(features, days_held)

            if exit_reason:
                pnl_raw = (exit_price - position["entry_price"]) * position["lots"]
                commission = position["entry_price"] * position["lots"] * COMMISSION_RT
                pnl = pnl_raw - commission
                equity += pnl
                peak_equity = max(peak_equity, equity)

                trades.append(Trade(
                    ticker=ticker,
                    entry_date=position["entry_date"],
                    exit_date=dt,
                    entry_price=position["entry_price"],
                    exit_price=exit_price,
                    lots=position["lots"],
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl / (position["entry_price"] * position["lots"]) * 100, 2),
                    days_held=days_held,
                    exit_reason=exit_reason,
                    claude_action=position.get("claude_action", ""),
                    claude_confidence=position.get("claude_confidence", 0.0),
                    algo_action=position.get("algo_action", ""),
                    claude_reasoning=position.get("claude_reasoning", ""),
                ))
                position = None

        # --- ENTRY check (only on Mondays) ---
        if position is None and dt in monday_set:
            # For Claude variant use relaxed signal to generate more candidates
            a_action = algo_signal(features, strict=not use_claude)

            if use_claude and a_action != "hold":
                # Calculate pre-score
                pre_score, breakdown = calculate_pre_score(
                    adx=safe_float(features.get("adx")),
                    di_plus=safe_float(features.get("di_plus")),
                    di_minus=safe_float(features.get("di_minus")),
                    rsi=safe_float(features.get("rsi_14")),
                    macd_hist=safe_float(features.get("macd_histogram")),
                    close=safe_float(features.get("close")),
                    ema20=safe_float(features.get("ema_20")),
                    ema50=safe_float(features.get("ema_50")),
                    ema200=safe_float(features.get("ema_200")),
                    volume_ratio=safe_float(features.get("volume_ratio_20"), 1.0),
                    obv_trend="flat",
                    sentiment_score=0.0,
                    direction="long",
                )

                if pre_score >= PRE_SCORE_THRESHOLD:
                    # Detect regime
                    regime_bars_up_to = [
                        c for c in regime_candles if c.dt <= dt
                    ]
                    if len(regime_bars_up_to) >= 14:
                        regime = detect_regime_from_index(regime_bars_up_to[-200:])
                    else:
                        regime = MarketRegime.WEAK_TREND

                    # Get USD/RUB
                    usd_rub = usd_rub_lookup.get(dt.isoformat(), 90.0)

                    # Portfolio context
                    dd_pct = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
                    portfolio_ctx = {
                        "cash_pct": 100.0,
                        "equity": equity,
                        "drawdown_pct": round(dd_pct * 100, 2),
                        "open_positions": [],
                    }
                    macro_ctx = {
                        "key_rate_pct": 21.0,  # CBR rate ~21% in 2024-2025
                        "usd_rub": usd_rub,
                        "oil_brent": None,
                    }

                    context_str = build_market_context(
                        ticker=ticker,
                        regime=regime,
                        features=features,
                        sentiment=0.0,
                        portfolio=portfolio_ctx,
                        macro=macro_ctx,
                    )

                    claude_resp, in_tok, out_tok = await call_claude(
                        dt, ticker, context_str, model, use_cache_only
                    )
                    claude_calls += 1
                    total_input_tokens += in_tok
                    total_output_tokens += out_tok

                    c_action = claude_resp.get("action", "hold")
                    c_confidence = float(claude_resp.get("confidence", 0.0))
                    c_reasoning = claude_resp.get("reasoning", "")

                    # Track divergence
                    if c_action != a_action:
                        divergent.append({
                            "date": dt.isoformat(),
                            "ticker": ticker,
                            "algo": a_action,
                            "claude": c_action,
                            "confidence": c_confidence,
                            "reasoning": c_reasoning[:200],
                            "pre_score": round(pre_score, 1),
                        })

                    # Claude overrides algo
                    if c_action == "hold" or c_confidence < CLAUDE_CONFIDENCE_THRESHOLD:
                        equity_curve.append(equity)
                        continue

                    # Proceed with entry using Claude recommendation
                    if c_action == "buy" and atr > 0:
                        stop_distance = atr * ATR_MULT
                        risk_amount = equity * RISK_PER_TRADE
                        lots = int(risk_amount / stop_distance)
                        pos_value = lots * close
                        max_value = equity * MAX_POSITION_PCT
                        if pos_value > max_value:
                            lots = int(max_value / close)

                        if lots > 0:
                            # Use Claude stop if provided, else algo stop
                            c_stop = claude_resp.get("stop_loss")
                            sl = c_stop if c_stop and c_stop > 0 else close - stop_distance

                            position = {
                                "entry_price": close,
                                "stop_loss": sl,
                                "lots": lots,
                                "entry_date": dt,
                                "claude_action": c_action,
                                "claude_confidence": c_confidence,
                                "algo_action": a_action,
                                "claude_reasoning": c_reasoning,
                            }
                else:
                    # Pre-score too low, hold
                    pass

            elif not use_claude and a_action == "buy" and atr > 0:
                # Algo-only entry
                stop_distance = atr * ATR_MULT
                risk_amount = equity * RISK_PER_TRADE
                lots = int(risk_amount / stop_distance)
                pos_value = lots * close
                max_value = equity * MAX_POSITION_PCT
                if pos_value > max_value:
                    lots = int(max_value / close)

                if lots > 0:
                    position = {
                        "entry_price": close,
                        "stop_loss": close - stop_distance,
                        "lots": lots,
                        "entry_date": dt,
                        "algo_action": a_action,
                        "claude_action": "",
                        "claude_confidence": 0.0,
                        "claude_reasoning": "",
                    }

        # Mark to market
        if position is not None:
            mtm = equity + (close - position["entry_price"]) * position["lots"]
        else:
            mtm = equity
        equity_curve.append(mtm)
        peak_equity = max(peak_equity, mtm)

    # Close remaining position
    if position is not None and rows:
        last = rows[-1]
        pnl_raw = (last["close"] - position["entry_price"]) * position["lots"]
        commission = position["entry_price"] * position["lots"] * COMMISSION_RT
        pnl = pnl_raw - commission
        equity += pnl
        trades.append(Trade(
            ticker=ticker,
            entry_date=position["entry_date"],
            exit_date=last["date"],
            entry_price=position["entry_price"],
            exit_price=last["close"],
            lots=position["lots"],
            pnl=round(pnl, 2),
            pnl_pct=round(pnl / (position["entry_price"] * position["lots"]) * 100, 2),
            days_held=(last["date"] - position["entry_date"]).days,
            exit_reason="end_of_data",
            claude_action=position.get("claude_action", ""),
            claude_confidence=position.get("claude_confidence", 0.0),
            algo_action=position.get("algo_action", ""),
            claude_reasoning=position.get("claude_reasoning", ""),
        ))

    sharpe = compute_sharpe(equity_curve)
    max_dd = compute_max_dd(equity_curve)
    return_pct = (equity / capital - 1) * 100

    result = TickerResult(
        ticker=ticker,
        trades=trades,
        final_equity=round(equity, 2),
        return_pct=round(return_pct, 2),
        sharpe=round(sharpe, 3),
        max_drawdown=round(max_dd * 100, 2),
        equity_curve=equity_curve,
    )
    return result, claude_calls, total_input_tokens, total_output_tokens, divergent


# ---------------------------------------------------------------------------
# Run full variant
# ---------------------------------------------------------------------------


async def run_variant(
    name: str,
    tickers: list[str],
    use_claude: bool,
    model: str,
    use_cache_only: bool,
    all_data: dict[str, pl.DataFrame],
    mondays: list[date],
    usd_rub: dict[str, float],
    regime_candles: dict[str, list[OHLCVBar]],
) -> BacktestVariantResult:
    log.info("variant_start", name=name, tickers=tickers, model=model if use_claude else "none")

    capital_per_ticker = INITIAL_CAPITAL / len(tickers)
    variant = BacktestVariantResult(name=name)

    for ticker in tickers:
        df = all_data.get(ticker)
        if df is None or len(df) < 250:
            log.warning("skip_ticker", ticker=ticker, reason="insufficient data")
            continue

        # Use the ticker's own candles for regime since IMOEX is too short
        rc = regime_candles.get(ticker, [])

        tr, calls, in_tok, out_tok, div = await run_ticker_backtest(
            ticker=ticker,
            df=df,
            mondays=mondays,
            capital=capital_per_ticker,
            use_claude=use_claude,
            model=model,
            use_cache_only=use_cache_only,
            usd_rub_lookup=usd_rub,
            regime_candles=rc,
        )
        variant.ticker_results.append(tr)
        variant.claude_calls += calls
        variant.claude_input_tokens += in_tok
        variant.claude_output_tokens += out_tok
        variant.divergent_decisions.extend(div)

        wins = sum(1 for t in tr.trades if t.pnl > 0)
        total = len(tr.trades)
        wr = wins / total * 100 if total > 0 else 0
        log.info("ticker_done",
                 variant=name, ticker=ticker,
                 trades=total, wins=wins,
                 win_rate=f"{wr:.0f}%",
                 return_pct=f"{tr.return_pct:+.1f}%",
                 sharpe=f"{tr.sharpe:.3f}",
                 max_dd=f"{tr.max_drawdown:.1f}%",
                 claude_calls=calls)

    variant.total_equity = sum(r.final_equity for r in variant.ticker_results)
    variant.total_return_pct = round(
        (variant.total_equity / INITIAL_CAPITAL - 1) * 100, 2
    )
    variant.total_trades = sum(len(r.trades) for r in variant.ticker_results)
    variant.total_wins = sum(
        sum(1 for t in r.trades if t.pnl > 0) for r in variant.ticker_results
    )

    # Aggregate equity curves for Sharpe/DD
    all_eq = []
    for r in variant.ticker_results:
        if len(r.equity_curve) > len(all_eq):
            all_eq = [0.0] * len(r.equity_curve)
        for i, v in enumerate(r.equity_curve):
            if i < len(all_eq):
                all_eq[i] += v
            else:
                all_eq.append(v)
    variant.total_sharpe = round(compute_sharpe(all_eq), 3) if all_eq else 0.0
    variant.total_max_dd = round(compute_max_dd(all_eq) * 100, 2) if all_eq else 0.0

    # Cost
    if model == MODEL_HAIKU:
        variant.claude_cost_usd = round(
            variant.claude_input_tokens / 1e6 * COST_HAIKU_INPUT
            + variant.claude_output_tokens / 1e6 * COST_HAIKU_OUTPUT,
            4,
        )
    else:
        variant.claude_cost_usd = round(
            variant.claude_input_tokens / 1e6 * COST_SONNET_INPUT
            + variant.claude_output_tokens / 1e6 * COST_SONNET_OUTPUT,
            4,
        )

    return variant


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_variant_table(v: BacktestVariantResult) -> None:
    wr = v.total_wins / v.total_trades * 100 if v.total_trades > 0 else 0
    print(f"\n--- {v.name} ---")
    print(f"{'Тикер':<8} {'Сделок':>7} {'Win%':>6} {'Доход%':>8} {'Sharpe':>8} {'MaxDD%':>8}")
    print("-" * 50)
    for r in v.ticker_results:
        t_wr = sum(1 for t in r.trades if t.pnl > 0) / len(r.trades) * 100 if r.trades else 0
        print(f"{r.ticker:<8} {len(r.trades):>7} {t_wr:>5.0f}% {r.return_pct:>+7.1f}% {r.sharpe:>8.3f} {r.max_drawdown:>7.1f}%")
    print("-" * 50)
    print(f"{'ИТОГО':<8} {v.total_trades:>7} {wr:>5.0f}% {v.total_return_pct:>+7.1f}% {v.total_sharpe:>8.3f} {v.total_max_dd:>7.1f}%")


def print_comparison(a: BacktestVariantResult, b: BacktestVariantResult) -> None:
    print("\n=== РАЗНИЦА (Algo vs Claude) ===")
    print(f"{'Метрика':<20} {'Без Claude':>12} {'С Claude':>12} {'Дельта':>12}")
    print("-" * 60)

    wr_a = a.total_wins / a.total_trades * 100 if a.total_trades else 0
    wr_b = b.total_wins / b.total_trades * 100 if b.total_trades else 0

    rows = [
        ("Доход%", f"{a.total_return_pct:+.1f}%", f"{b.total_return_pct:+.1f}%",
         f"{b.total_return_pct - a.total_return_pct:+.1f}%"),
        ("Sharpe", f"{a.total_sharpe:.3f}", f"{b.total_sharpe:.3f}",
         f"{b.total_sharpe - a.total_sharpe:+.3f}"),
        ("MaxDD%", f"{a.total_max_dd:.1f}%", f"{b.total_max_dd:.1f}%",
         f"{b.total_max_dd - a.total_max_dd:+.1f}%"),
        ("Сделок", str(a.total_trades), str(b.total_trades),
         f"{b.total_trades - a.total_trades:+d}"),
        ("Win%", f"{wr_a:.0f}%", f"{wr_b:.0f}%", f"{wr_b - wr_a:+.0f}%"),
    ]
    for label, va, vb, delta in rows:
        print(f"{label:<20} {va:>12} {vb:>12} {delta:>12}")


def print_claude_examples(v: BacktestVariantResult) -> None:
    # Best trades with Claude action
    claude_trades = [
        t for r in v.ticker_results for t in r.trades if t.claude_action
    ]
    if not claude_trades:
        print("\n[Нет сделок с Claude]")
        return

    sorted_best = sorted(claude_trades, key=lambda t: t.pnl, reverse=True)

    print("\n=== ТОП-5 ЛУЧШИХ РЕШЕНИЙ CLAUDE ===")
    for t in sorted_best[:5]:
        print(f"  {t.ticker} {t.entry_date} -> {t.exit_date} "
              f"PnL={t.pnl:+,.0f} ({t.pnl_pct:+.1f}%) "
              f"[conf={t.claude_confidence:.2f}] "
              f"{t.claude_reasoning[:100]}")

    print("\n=== ТОП-5 ХУДШИХ РЕШЕНИЙ CLAUDE ===")
    for t in sorted_best[-5:]:
        print(f"  {t.ticker} {t.entry_date} -> {t.exit_date} "
              f"PnL={t.pnl:+,.0f} ({t.pnl_pct:+.1f}%) "
              f"[conf={t.claude_confidence:.2f}] "
              f"{t.claude_reasoning[:100]}")


def print_divergent_examples(v: BacktestVariantResult) -> None:
    if not v.divergent_decisions:
        return
    print(f"\n=== РАСХОЖДЕНИЯ ALGO vs CLAUDE ({len(v.divergent_decisions)} шт.) ===")
    for d in v.divergent_decisions[:10]:
        print(f"  {d['date']} {d['ticker']}: algo={d['algo']} claude={d['claude']} "
              f"conf={d['confidence']:.2f} score={d['pre_score']} "
              f"| {d['reasoning'][:80]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest with Claude API")
    parser.add_argument("--skip-claude", action="store_true",
                        help="Run algo-only, no Claude API calls")
    parser.add_argument("--use-cache", action="store_true",
                        help="Use only cached Claude responses, no new API calls")
    parser.add_argument("--no-sonnet", action="store_true",
                        help="Skip Sonnet variant (saves money)")
    args = parser.parse_args()

    init_cache(DB_PATH)

    print("=" * 65)
    print("  BACKTEST C CLAUDE API (2024-01 -- 2026-03)")
    print("  Тикеры:", ", ".join(TICKERS))
    print("  Капитал:", f"{INITIAL_CAPITAL:,.0f} RUB")
    print("  Решения: каждый понедельник")
    print("=" * 65)

    # Load data
    log.info("loading_data")
    all_candles: dict[str, list[OHLCVBar]] = {}
    all_dfs: dict[str, pl.DataFrame] = {}

    for ticker in TICKERS:
        candles = load_candles_sync(DB_PATH, ticker)
        all_candles[ticker] = candles
        df = candles_to_df(candles)
        df = add_all_indicators(df)
        all_dfs[ticker] = df
        log.info("data_loaded", ticker=ticker, bars=len(candles))

    usd_rub = load_macro_usd_rub(DB_PATH)
    mondays = get_mondays(START_DATE, END_DATE)
    log.info("decision_points", mondays=len(mondays))

    # --- Variant A: Algo only ---
    variant_a = await run_variant(
        name="A: Только алгоритм (без Claude)",
        tickers=TICKERS,
        use_claude=False,
        model="",
        use_cache_only=False,
        all_data=all_dfs,
        mondays=mondays,
        usd_rub=usd_rub,
        regime_candles=all_candles,
    )

    # --- Variant B: Claude Haiku ---
    if args.skip_claude:
        variant_b = None
        log.info("skipping_claude", reason="--skip-claude flag")
    else:
        variant_b = await run_variant(
            name="B: С Claude Haiku",
            tickers=TICKERS,
            use_claude=True,
            model=MODEL_HAIKU,
            use_cache_only=args.use_cache,
            all_data=all_dfs,
            mondays=mondays,
            usd_rub=usd_rub,
            regime_candles=all_candles,
        )

    # --- Variant C: Claude Sonnet (SBER only, ~2 months to save cost) ---
    variant_c = None
    if not args.skip_claude and not args.no_sonnet:
        sonnet_mondays = [m for m in mondays if date(2025, 1, 1) <= m <= date(2025, 2, 28)]
        if sonnet_mondays:
            # Build df limited to that period
            variant_c = await run_variant(
                name="C: С Claude Sonnet (SBER, 2 мес)",
                tickers=["SBER"],
                use_claude=True,
                model=MODEL_SONNET,
                use_cache_only=args.use_cache,
                all_data=all_dfs,
                mondays=sonnet_mondays,
                usd_rub=usd_rub,
                regime_candles=all_candles,
            )

    # --- Print results ---
    print("\n" + "=" * 65)
    print("  РЕЗУЛЬТАТЫ БЭКТЕСТА С CLAUDE (2024-2026)")
    print("=" * 65)

    print_variant_table(variant_a)

    if variant_b:
        print_variant_table(variant_b)
        print_comparison(variant_a, variant_b)
        print_claude_examples(variant_b)
        print_divergent_examples(variant_b)

    if variant_c:
        print_variant_table(variant_c)

    # --- Cost summary ---
    print("\n=== СТОИМОСТЬ CLAUDE API ===")
    if variant_b:
        print(f"  Haiku:  вызовов={variant_b.claude_calls}, "
              f"input={variant_b.claude_input_tokens:,} tok, "
              f"output={variant_b.claude_output_tokens:,} tok, "
              f"стоимость=${variant_b.claude_cost_usd:.4f}")
    if variant_c:
        print(f"  Sonnet: вызовов={variant_c.claude_calls}, "
              f"input={variant_c.claude_input_tokens:,} tok, "
              f"output={variant_c.claude_output_tokens:,} tok, "
              f"стоимость=${variant_c.claude_cost_usd:.4f}")

    total_cost = (variant_b.claude_cost_usd if variant_b else 0) + (variant_c.claude_cost_usd if variant_c else 0)
    print(f"  ИТОГО: ${total_cost:.4f}")

    # Cache stats
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT model, COUNT(*) FROM claude_cache GROUP BY model")
    cache_stats = cur.fetchall()
    conn.close()
    if cache_stats:
        print("\n=== КЕШ CLAUDE ===")
        for model_name, cnt in cache_stats:
            print(f"  {model_name}: {cnt} записей в кеше")


if __name__ == "__main__":
    asyncio.run(main())
