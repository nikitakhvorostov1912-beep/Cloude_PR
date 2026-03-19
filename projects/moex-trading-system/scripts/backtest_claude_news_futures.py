"""Backtest USDRUB futures with Claude + sentiment (synthetic + live RSS).

Compares four variants:
  A) Algorithm only (EMA cross + ADX trend following) -- baseline
  B) Claude WITHOUT sentiment (sentiment=0)
  C) Claude WITH synthetic sentiment (derived from price movement)
  D) Claude WITH real RSS news (last 2 weeks only -- live test)

Claude responses are cached in SQLite; re-runs are free.

Usage:
    python -m scripts.backtest_claude_news_futures
    python -m scripts.backtest_claude_news_futures --skip-claude
    python -m scripts.backtest_claude_news_futures --use-cache
    python -m scripts.backtest_claude_news_futures --no-live
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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

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
    calculate_rsi,
    calculate_stochastic,
)
from src.analysis.regime import detect_regime_from_index
from src.data.news_parser import fetch_news, parse_feed, FEEDS
from src.models.market import MarketRegime, OHLCVBar

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
TICKER = "USDRUB"
START_DATE = date(2024, 1, 1)
END_DATE = date(2026, 3, 18)
INITIAL_CAPITAL = 1_000_000.0
POSITION_SIZE_PCT = 0.10  # 10% of equity per trade
COMMISSION_PER_SIDE = 0.0001  # 0.01% futures commission
ATR_STOP_MULT = 2.0
ATR_TARGET_MULT = 3.0
TIME_STOP_DAYS = 20
CLAUDE_CONFIDENCE_THRESHOLD = 0.40
API_DELAY = 0.5

MODEL_HAIKU = "claude-haiku-4-5-20251001"

COST_HAIKU_INPUT = 0.80
COST_HAIKU_OUTPUT = 4.00

# Keywords for filtering USD/RUB relevant news
NEWS_KEYWORDS = [
    "ruble", "rouble", "dollar", "usd", "rub",
    "rubl", "dollay", "kurs", "cbr", "stavk",
    "neft", "brent", "sankci", "sanction",
]
NEWS_KEYWORDS_RU = [
    "rubly", "dollar", "kurs", "cbr",
]

SIGNAL_TOOL: dict = {
    "name": "submit_trading_signal",
    "description": "Submit trading signal for USD/RUB futures based on market analysis",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
            "direction": {"type": "string", "enum": ["long", "short"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "entry_price": {"type": "number"},
            "stop_loss": {"type": "number"},
            "take_profit": {"type": "number"},
            "reasoning": {"type": "string"},
            "key_factors": {"type": "array", "items": {"type": "string"}},
            "risk_factors": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["action", "direction", "confidence", "reasoning"],
    },
}

SYSTEM_PROMPT_USDRUB = (
    "Ty -- sistematicheskij analtik valyutnogo rynka (USD/RUB futures, MOEX).\n\n"
    "Pravila:\n"
    "1. NE ispolnyaesh sdelki -- tolko formiruesh signal\n"
    "2. Pri neopredelyonnosti -- HOLD\n"
    "3. Stop-loss obyazatelen dlya BUY/SELL\n"
    "4. BUY = dollar rastyot / rubl slabeet\n"
    "5. SELL = dollar padaet / rubl krepnet\n"
    "6. Uchityvaj sentiment novostej esli on dostopen\n"
    "7. Pri protivorechivyh indikatorah -- umenshit confidence\n\n"
    "Otvet STROGO v formate JSON cherez tool_use."
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Trade:
    direction: str  # "long" or "short"
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    position_value: float
    gross_pnl: float
    commission: float
    net_pnl: float
    pnl_pct: float
    days_held: int
    exit_reason: str
    claude_action: str = ""
    claude_confidence: float = 0.0
    claude_reasoning: str = ""
    sentiment_used: float = 0.0


@dataclass
class VariantResult:
    name: str
    trades: list[Trade] = field(default_factory=list)
    final_equity: float = 0.0
    return_pct: float = 0.0
    sharpe: float = 0.0
    max_drawdown_pct: float = 0.0
    equity_curve: list[float] = field(default_factory=list)
    claude_calls: int = 0
    claude_input_tokens: int = 0
    claude_output_tokens: int = 0
    claude_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Cache (reuses existing claude_cache table, adds sentiment_score to hash)
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

# We need a separate cache key for sentiment vs no-sentiment calls.
# Use ticker suffix: USDRUB_s0.0 vs USDRUB_s-0.5

def _cache_ticker(ticker: str, sentiment: float) -> str:
    """Build cache-safe ticker key that differentiates sentiment variants."""
    return f"{ticker}_s{sentiment:.2f}"


def init_cache(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(CACHE_DDL)
    conn.commit()
    conn.close()


def get_cached_response(db_path: str, dt: date, cache_key: str, model: str) -> dict | None:
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT response, input_tokens, output_tokens FROM claude_cache "
        "WHERE date = ? AND ticker = ? AND model = ?",
        (dt.isoformat(), cache_key, model),
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
    db_path: str, dt: date, cache_key: str, model: str,
    input_hash: str, response: dict, input_tokens: int, output_tokens: int,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO claude_cache "
        "(date, ticker, model, input_hash, response, input_tokens, output_tokens) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (dt.isoformat(), cache_key, model, input_hash,
         json.dumps(response, ensure_ascii=False), input_tokens, output_tokens),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_usdrub_candles(db_path: str) -> list[OHLCVBar]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT ticker, date, open, high, low, close, volume, value "
        "FROM candles WHERE ticker = ? ORDER BY date ASC",
        (TICKER,),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        OHLCVBar(
            ticker=row["ticker"], dt=date.fromisoformat(row["date"]),
            open=row["open"], high=row["high"], low=row["low"],
            close=row["close"], volume=row["volume"], value=row["value"],
        )
        for row in rows
    ]


def candles_to_df(candles: list[OHLCVBar]) -> pl.DataFrame:
    return pl.DataFrame({
        "date": [c.dt for c in candles],
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
        "volume": [c.volume for c in candles],
    }).sort("date")


def add_indicators(df: pl.DataFrame) -> pl.DataFrame:
    close = df["close"]
    high = df["high"]
    low = df["low"]

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

    return df.with_columns(cols)


def safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def get_features(row: dict) -> dict:
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
    }


# ---------------------------------------------------------------------------
# Synthetic sentiment from price movement
# ---------------------------------------------------------------------------


def compute_synthetic_sentiment(
    rows: list[dict], current_idx: int, lookback: int = 5,
) -> float:
    """Derive synthetic sentiment from USD/RUB weekly price change.

    If USD/RUB rose > 2% over lookback days -> sentiment = -0.5 (negative for RUB)
    If USD/RUB fell > 2% -> sentiment = +0.5 (positive for RUB)
    Otherwise -> 0.0 (neutral)
    """
    if current_idx < lookback:
        return 0.0

    current_close = safe_float(rows[current_idx].get("close"))
    prev_close = safe_float(rows[current_idx - lookback].get("close"))

    if prev_close == 0:
        return 0.0

    change_pct = (current_close - prev_close) / prev_close

    if change_pct > 0.02:
        return -0.5  # USD strengthened = negative RUB sentiment
    elif change_pct < -0.02:
        return 0.5   # USD weakened = positive RUB sentiment
    elif change_pct > 0.01:
        return -0.25
    elif change_pct < -0.01:
        return 0.25
    return 0.0


# ---------------------------------------------------------------------------
# News sentiment (live RSS)
# ---------------------------------------------------------------------------


def _is_usdrub_relevant(title: str, summary: str) -> bool:
    """Check if a news article is relevant to USD/RUB."""
    text = (title + " " + (summary or "")).lower()
    keywords = [
        "rubl", "rubly", "dollar", "usd/rub", "kurs", "valyut",
        "cbr", "stavk", "neft", "brent", "sankci",
        # Cyrillic
        "\u0440\u0443\u0431\u043b",  # rubly
        "\u0434\u043e\u043b\u043b\u0430\u0440",  # dollar
        "\u043a\u0443\u0440\u0441",  # kurs
        "\u0432\u0430\u043b\u044e\u0442",  # valyut
        "\u0426\u0411",  # CB
        "\u0441\u0442\u0430\u0432\u043a",  # stavk
        "\u043d\u0435\u0444\u0442",  # neft
        "\u0441\u0430\u043d\u043a\u0446\u0438",  # sankci
    ]
    return any(kw in text for kw in keywords)


async def fetch_live_news_sentiment() -> list[dict]:
    """Fetch current RSS news and return relevant articles for USD/RUB.

    Returns list of dicts with keys: title, summary, published, source.
    """
    try:
        articles = await fetch_news(hours_back=336, known_tickers=[])  # ~14 days
    except Exception as exc:
        log.warning("rss_fetch_failed", error=str(exc))
        return []

    relevant = []
    for art in articles:
        title = art.get("title", "")
        summary = art.get("summary", "") or ""
        if _is_usdrub_relevant(title, summary):
            relevant.append({
                "title": title,
                "summary": summary[:300],
                "published": str(art.get("published", "")),
                "source": art.get("source", ""),
            })

    log.info("live_news_fetched", total=len(articles), relevant=len(relevant))
    return relevant[:30]  # limit to 30 most relevant


async def score_news_sentiment_claude(
    articles: list[dict],
) -> tuple[float, list[dict]]:
    """Use Claude Haiku to score sentiment of news articles for USD/RUB.

    Returns (avg_sentiment_score, scored_articles_list).
    """
    if not articles:
        return 0.0, []

    # Batch articles into one prompt for efficiency
    news_text = "\n".join(
        f"{i+1}. [{a['source']}] {a['title']}"
        for i, a in enumerate(articles[:15])  # limit to 15
    )

    prompt = (
        "Oceni sentiment kazhdoj novosti po shkale ot -1.0 do +1.0 "
        "otnositelno USDRUB (dollar/rubl).\n"
        "+1.0 = dollar rastyot / rubl slabeet (BUY USDRUB)\n"
        "-1.0 = dollar padaet / rubl krepnet (SELL USDRUB)\n"
        "0.0 = nejtralno\n\n"
        f"Novosti:\n{news_text}\n\n"
        "Otvet v formate JSON massiva: [{\"idx\": 1, \"score\": 0.3, \"reason\": \"...\"}, ...]"
    )

    client = anthropic.AsyncAnthropic()
    try:
        response = await client.messages.create(
            model=MODEL_HAIKU,
            max_tokens=1024,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        log.warning("sentiment_api_error", error=str(exc))
        return 0.0, []

    # Parse response
    text = response.content[0].text if response.content else ""
    scored = []
    try:
        # Find JSON array in response
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            items = json.loads(text[start:end])
            for item in items:
                idx = int(item.get("idx", 0)) - 1
                score = float(item.get("score", 0))
                reason = item.get("reason", "")
                if 0 <= idx < len(articles):
                    scored.append({
                        "title": articles[idx]["title"][:80],
                        "score": score,
                        "reason": reason,
                    })
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        log.warning("sentiment_parse_error", error=str(exc))
        return 0.0, []

    if not scored:
        return 0.0, []

    avg_score = sum(s["score"] for s in scored) / len(scored)
    return round(avg_score, 3), scored


# ---------------------------------------------------------------------------
# Build context for Claude
# ---------------------------------------------------------------------------


def build_usdrub_context(
    features: dict,
    sentiment_score: float,
    sentiment_label: str,
    sentiment_details: str,
    regime: str,
    equity: float,
    drawdown_pct: float,
    position_info: str,
) -> str:
    """Build structured context for Claude USDRUB analysis."""
    ctx = {
        "instrument": "USDRUB (futures Si)",
        "market_regime": regime,
        "price": {
            "close": safe_float(features.get("close")),
            "ema_20": safe_float(features.get("ema_20")),
            "ema_50": safe_float(features.get("ema_50")),
            "ema_200": safe_float(features.get("ema_200")),
        },
        "trend": {
            "adx": safe_float(features.get("adx")),
            "di_plus": safe_float(features.get("di_plus")),
            "di_minus": safe_float(features.get("di_minus")),
        },
        "momentum": {
            "rsi_14": safe_float(features.get("rsi_14")),
            "macd_histogram": safe_float(features.get("macd_histogram")),
            "stoch_k": safe_float(features.get("stoch_k")),
        },
        "volatility": {
            "atr_14": safe_float(features.get("atr_14")),
            "bb_pct_b": safe_float(features.get("bb_pct_b")),
        },
        "sentiment": {
            "score": sentiment_score,
            "label": sentiment_label,
            "details": sentiment_details,
        },
        "macro": {
            "key_rate_pct": 21.0,
        },
        "portfolio": {
            "equity": round(equity, 0),
            "drawdown_pct": round(drawdown_pct, 2),
            "position": position_info,
        },
    }
    return json.dumps(ctx, ensure_ascii=False, indent=None)


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------


async def call_claude_usdrub(
    dt: date,
    context_str: str,
    sentiment_score: float,
    use_cache_only: bool = False,
) -> tuple[dict, int, int]:
    """Call Claude API for USDRUB signal with caching."""
    cache_key = _cache_ticker(TICKER, sentiment_score)
    cached = get_cached_response(DB_PATH, dt, cache_key, MODEL_HAIKU)
    if cached is not None:
        return cached["response"], cached["input_tokens"], cached["output_tokens"]

    if use_cache_only:
        return {"action": "hold", "direction": "long", "confidence": 0.0,
                "reasoning": "cache miss"}, 0, 0

    input_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]

    user_message = (
        f"Proanalziruj USDRUB futures i sformiruj torgovyj signal.\n\n"
        f"Kontekst rynka:\n{context_str}"
    )

    client = anthropic.AsyncAnthropic()
    try:
        response = await client.messages.create(
            model=MODEL_HAIKU,
            max_tokens=1024,
            temperature=0.1,
            system=SYSTEM_PROMPT_USDRUB,
            tools=[SIGNAL_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        log.error("claude_api_error", date=str(dt), error=str(exc))
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

    save_cached_response(DB_PATH, dt, cache_key, MODEL_HAIKU,
                         input_hash, parsed, input_tokens, output_tokens)

    await asyncio.sleep(API_DELAY)
    return parsed, input_tokens, output_tokens


# ---------------------------------------------------------------------------
# Algorithmic signal (baseline)
# ---------------------------------------------------------------------------


def algo_signal(features: dict) -> str:
    """EMA crossover + ADX trend following for USDRUB.

    Returns "buy", "sell", or "hold".
    - BUY: EMA20 > EMA50 and ADX > 25 (dollar strengthening)
    - SELL: EMA20 < EMA50 and ADX > 25 (dollar weakening)
    """
    ema20 = safe_float(features.get("ema_20"))
    ema50 = safe_float(features.get("ema_50"))
    adx = safe_float(features.get("adx"))

    if adx < 25:
        return "hold"

    if ema20 > ema50:
        return "buy"   # long USDRUB = dollar up
    elif ema20 < ema50:
        return "sell"   # short USDRUB = dollar down
    return "hold"


def algo_exit_check(
    features: dict, direction: str, days_held: int,
    entry_price: float, current_price: float, stop_loss: float, take_profit: float,
) -> str | None:
    """Check exit conditions for open position."""
    rsi = safe_float(features.get("rsi_14"))
    ema20 = safe_float(features.get("ema_20"))
    ema50 = safe_float(features.get("ema_50"))

    if direction == "long":
        if current_price <= stop_loss:
            return "stop_loss"
        if current_price >= take_profit:
            return "take_profit"
        if ema20 < ema50:
            return "trend_reversal"
    else:  # short
        if current_price >= stop_loss:
            return "stop_loss"
        if current_price <= take_profit:
            return "take_profit"
        if ema20 > ema50:
            return "trend_reversal"

    if direction == "long" and rsi > 75:
        return "rsi_overbought"
    if direction == "short" and rsi < 25:
        return "rsi_oversold"

    if days_held >= TIME_STOP_DAYS:
        return "time_stop"

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_mondays(start: date, end: date) -> list[date]:
    mondays = []
    d = start
    while d.weekday() != 0:
        d += timedelta(days=1)
    while d <= end:
        mondays.append(d)
        d += timedelta(days=7)
    return mondays


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
        return 0.0
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


def sentiment_label(score: float) -> str:
    if score > 0.2:
        return "bullish_rub"
    if score < -0.2:
        return "bearish_rub"
    return "neutral"


# ---------------------------------------------------------------------------
# Run backtest variant
# ---------------------------------------------------------------------------


async def run_variant(
    name: str,
    rows: list[dict],
    date_to_idx: dict[date, int],
    mondays: list[date],
    candles: list[OHLCVBar],
    capital: float,
    use_claude: bool,
    use_sentiment: bool,
    use_cache_only: bool,
    live_sentiment_score: float | None = None,
    live_news_start: date | None = None,
) -> VariantResult:
    """Run one variant of the backtest."""
    log.info("variant_start", name=name, use_claude=use_claude,
             use_sentiment=use_sentiment)

    result = VariantResult(name=name)
    equity = capital
    peak_equity = capital
    equity_curve = [capital]
    position = None  # dict or None
    monday_set = set(mondays)

    for i, row in enumerate(rows):
        dt = row["date"]
        if dt < START_DATE:
            equity_curve.append(equity)
            continue

        close = row["close"]
        features = get_features(row)
        atr = safe_float(features.get("atr_14"))

        # Skip if indicators not ready
        if any(safe_float(features.get(k)) == 0.0
               for k in ["rsi_14", "ema_50", "adx", "atr_14"]):
            equity_curve.append(equity)
            continue

        # --- EXIT check (every day) ---
        if position is not None:
            days_held = (dt - position["entry_date"]).days
            exit_reason = algo_exit_check(
                features, position["direction"], days_held,
                position["entry_price"], close,
                position["stop_loss"], position["take_profit"],
            )

            if exit_reason:
                entry_p = position["entry_price"]
                pos_val = position["position_value"]
                units = pos_val / entry_p

                if position["direction"] == "long":
                    gross_pnl = (close - entry_p) * units
                else:
                    gross_pnl = (entry_p - close) * units

                commission = pos_val * COMMISSION_PER_SIDE * 2
                net_pnl = gross_pnl - commission
                equity += net_pnl
                peak_equity = max(peak_equity, equity)

                result.trades.append(Trade(
                    direction=position["direction"],
                    entry_date=position["entry_date"],
                    exit_date=dt,
                    entry_price=entry_p,
                    exit_price=close,
                    position_value=pos_val,
                    gross_pnl=round(gross_pnl, 2),
                    commission=round(commission, 2),
                    net_pnl=round(net_pnl, 2),
                    pnl_pct=round(net_pnl / pos_val * 100, 2),
                    days_held=days_held,
                    exit_reason=exit_reason,
                    claude_action=position.get("claude_action", ""),
                    claude_confidence=position.get("claude_confidence", 0.0),
                    claude_reasoning=position.get("claude_reasoning", ""),
                    sentiment_used=position.get("sentiment_used", 0.0),
                ))
                position = None

        # --- ENTRY check (only on Mondays) ---
        if position is None and dt in monday_set:
            a_signal = algo_signal(features)

            if use_claude and a_signal != "hold":
                # Compute sentiment
                sent_score = 0.0
                sent_details = "sentiment unavailable"

                if use_sentiment:
                    # Check if we're in the live period
                    if (live_sentiment_score is not None
                            and live_news_start is not None
                            and dt >= live_news_start):
                        sent_score = live_sentiment_score
                        sent_details = "live RSS news sentiment"
                    else:
                        sent_score = compute_synthetic_sentiment(rows, i)
                        sent_details = f"synthetic (price change based), score={sent_score}"

                sent_lbl = sentiment_label(sent_score)

                # Detect regime
                regime_bars = [c for c in candles if c.dt <= dt]
                if len(regime_bars) >= 50:
                    try:
                        regime = detect_regime_from_index(regime_bars[-200:])
                    except Exception:
                        regime = MarketRegime.WEAK_TREND
                else:
                    regime = MarketRegime.WEAK_TREND

                dd_pct = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0.0
                pos_info = "no open positions"

                context_str = build_usdrub_context(
                    features=features,
                    sentiment_score=sent_score,
                    sentiment_label=sent_lbl,
                    sentiment_details=sent_details,
                    regime=regime.value,
                    equity=equity,
                    drawdown_pct=dd_pct,
                    position_info=pos_info,
                )

                claude_resp, in_tok, out_tok = await call_claude_usdrub(
                    dt, context_str, sent_score, use_cache_only,
                )
                result.claude_calls += 1
                result.claude_input_tokens += in_tok
                result.claude_output_tokens += out_tok

                c_action = claude_resp.get("action", "hold")
                c_confidence = float(claude_resp.get("confidence", 0.0))
                c_reasoning = claude_resp.get("reasoning", "")

                if c_action == "hold" or c_confidence < CLAUDE_CONFIDENCE_THRESHOLD:
                    equity_curve.append(equity)
                    continue

                # Determine direction
                if c_action == "buy":
                    direction = "long"
                elif c_action == "sell":
                    direction = "short"
                else:
                    equity_curve.append(equity)
                    continue

                if atr > 0:
                    stop_dist = atr * ATR_STOP_MULT
                    target_dist = atr * ATR_TARGET_MULT
                    pos_val = equity * POSITION_SIZE_PCT

                    if direction == "long":
                        sl = close - stop_dist
                        tp = close + target_dist
                    else:
                        sl = close + stop_dist
                        tp = close - target_dist

                    # Use Claude's stop/target if provided
                    c_stop = claude_resp.get("stop_loss")
                    c_tp = claude_resp.get("take_profit")
                    if c_stop and c_stop > 0:
                        sl = c_stop
                    if c_tp and c_tp > 0:
                        tp = c_tp

                    position = {
                        "direction": direction,
                        "entry_price": close,
                        "entry_date": dt,
                        "stop_loss": sl,
                        "take_profit": tp,
                        "position_value": pos_val,
                        "claude_action": c_action,
                        "claude_confidence": c_confidence,
                        "claude_reasoning": c_reasoning,
                        "sentiment_used": sent_score,
                    }

            elif not use_claude and a_signal != "hold" and atr > 0:
                # Pure algo entry
                direction = "long" if a_signal == "buy" else "short"
                stop_dist = atr * ATR_STOP_MULT
                target_dist = atr * ATR_TARGET_MULT
                pos_val = equity * POSITION_SIZE_PCT

                if direction == "long":
                    sl = close - stop_dist
                    tp = close + target_dist
                else:
                    sl = close + stop_dist
                    tp = close - target_dist

                position = {
                    "direction": direction,
                    "entry_price": close,
                    "entry_date": dt,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "position_value": pos_val,
                    "claude_action": "",
                    "claude_confidence": 0.0,
                    "claude_reasoning": "",
                    "sentiment_used": 0.0,
                }

        # Mark to market
        if position is not None:
            entry_p = position["entry_price"]
            pos_val = position["position_value"]
            units = pos_val / entry_p
            if position["direction"] == "long":
                mtm = equity + (close - entry_p) * units
            else:
                mtm = equity + (entry_p - close) * units
        else:
            mtm = equity
        equity_curve.append(mtm)
        peak_equity = max(peak_equity, mtm)

    # Close open position at end
    if position is not None and rows:
        last = rows[-1]
        close = last["close"]
        entry_p = position["entry_price"]
        pos_val = position["position_value"]
        units = pos_val / entry_p
        days_held = (last["date"] - position["entry_date"]).days

        if position["direction"] == "long":
            gross_pnl = (close - entry_p) * units
        else:
            gross_pnl = (entry_p - close) * units

        commission = pos_val * COMMISSION_PER_SIDE * 2
        net_pnl = gross_pnl - commission
        equity += net_pnl

        result.trades.append(Trade(
            direction=position["direction"],
            entry_date=position["entry_date"],
            exit_date=last["date"],
            entry_price=entry_p,
            exit_price=close,
            position_value=pos_val,
            gross_pnl=round(gross_pnl, 2),
            commission=round(commission, 2),
            net_pnl=round(net_pnl, 2),
            pnl_pct=round(net_pnl / pos_val * 100, 2),
            days_held=days_held,
            exit_reason="end_of_data",
            claude_action=position.get("claude_action", ""),
            claude_confidence=position.get("claude_confidence", 0.0),
            claude_reasoning=position.get("claude_reasoning", ""),
            sentiment_used=position.get("sentiment_used", 0.0),
        ))

    result.final_equity = round(equity, 2)
    result.return_pct = round((equity / capital - 1) * 100, 2)
    result.sharpe = round(compute_sharpe(equity_curve), 3)
    result.max_drawdown_pct = round(compute_max_dd(equity_curve) * 100, 2)
    result.equity_curve = equity_curve
    result.claude_cost_usd = round(
        result.claude_input_tokens / 1e6 * COST_HAIKU_INPUT
        + result.claude_output_tokens / 1e6 * COST_HAIKU_OUTPUT,
        4,
    )

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _win_rate(v: VariantResult) -> float:
    wins = sum(1 for t in v.trades if t.net_pnl > 0)
    return wins / len(v.trades) * 100 if v.trades else 0.0


def print_variant(v: VariantResult) -> None:
    wr = _win_rate(v)
    longs = sum(1 for t in v.trades if t.direction == "long")
    shorts = sum(1 for t in v.trades if t.direction == "short")
    print(f"\n--- {v.name} ---")
    print(f"  Kapital: {INITIAL_CAPITAL:,.0f} -> {v.final_equity:,.0f} RUB")
    print(f"  Dokhod:  {v.return_pct:+.2f}%")
    print(f"  Sharpe:  {v.sharpe:.3f}")
    print(f"  MaxDD:   {v.max_drawdown_pct:.2f}%")
    print(f"  Sdelok:  {len(v.trades)} (long={longs}, short={shorts})")
    print(f"  Win%:    {wr:.0f}%")
    if v.claude_calls > 0:
        print(f"  Claude:  {v.claude_calls} calls, ${v.claude_cost_usd:.4f}")


def print_comparison_table(variants: list[VariantResult]) -> None:
    print("\n" + "=" * 75)
    print("  SRAVNENIE VARIANTOV")
    print("=" * 75)
    header = f"{'Variant':<30} {'Dokhod%':>8} {'Sharpe':>8} {'Win%':>6} {'MaxDD%':>8} {'Sdelok':>7}"
    print(header)
    print("-" * 75)
    for v in variants:
        wr = _win_rate(v)
        print(f"{v.name:<30} {v.return_pct:>+7.2f}% {v.sharpe:>8.3f} {wr:>5.0f}% "
              f"{v.max_drawdown_pct:>7.2f}% {len(v.trades):>7}")


def print_sentiment_effect(b: VariantResult, c: VariantResult) -> None:
    print("\n=== EFFEKT SENTIMENT ===")
    print(f"  Variant B (bez sentiment):  dokhod={b.return_pct:+.2f}%, "
          f"win={_win_rate(b):.0f}%, sharpe={b.sharpe:.3f}")
    print(f"  Variant C (s sentiment):    dokhod={c.return_pct:+.2f}%, "
          f"win={_win_rate(c):.0f}%, sharpe={c.sharpe:.3f}")
    delta_ret = c.return_pct - b.return_pct
    delta_wr = _win_rate(c) - _win_rate(b)
    delta_sharpe = c.sharpe - b.sharpe
    print(f"  Delta: dokhod {delta_ret:+.2f}%, win {delta_wr:+.0f}%, sharpe {delta_sharpe:+.3f}")

    if delta_ret > 0.5 and delta_sharpe > 0:
        print("  -> Claude s sentiment prinimaet LUCHSHIE resheniya")
    elif delta_ret < -0.5 and delta_sharpe < 0:
        print("  -> Claude s sentiment prinimaet KHUDSHIE resheniya")
    else:
        print("  -> Raznica nezachitelnaya / ODINAKOVYE resheniya")


def print_trade_examples(v: VariantResult, label: str) -> None:
    claude_trades = [t for t in v.trades if t.claude_action]
    if not claude_trades:
        print(f"\n[Net sdelok s Claude v variante {label}]")
        return

    sorted_best = sorted(claude_trades, key=lambda t: t.net_pnl, reverse=True)

    print(f"\n=== TOP-5 LUCHSHIKH RESHENIJ CLAUDE ({label}) ===")
    for t in sorted_best[:5]:
        sent_str = f" sent={t.sentiment_used:+.2f}" if t.sentiment_used != 0 else ""
        print(f"  {t.direction.upper()} {t.entry_date}->{t.exit_date} "
              f"PnL={t.net_pnl:+,.0f} ({t.pnl_pct:+.1f}%) "
              f"[conf={t.claude_confidence:.2f}{sent_str}] "
              f"{t.claude_reasoning[:100]}")

    print(f"\n=== TOP-5 KHUDSHIKH RESHENIJ CLAUDE ({label}) ===")
    for t in sorted_best[-5:]:
        sent_str = f" sent={t.sentiment_used:+.2f}" if t.sentiment_used != 0 else ""
        print(f"  {t.direction.upper()} {t.entry_date}->{t.exit_date} "
              f"PnL={t.net_pnl:+,.0f} ({t.pnl_pct:+.1f}%) "
              f"[conf={t.claude_confidence:.2f}{sent_str}] "
              f"{t.claude_reasoning[:100]}")


def print_sentiment_examples(c: VariantResult) -> None:
    """Show trades where sentiment was non-zero and its impact."""
    sent_trades = [t for t in c.trades if abs(t.sentiment_used) > 0.01]
    if not sent_trades:
        print("\n[Net sdelok s nenulevym sentiment]")
        return

    positive = [t for t in sent_trades if t.net_pnl > 0]
    negative = [t for t in sent_trades if t.net_pnl <= 0]

    print(f"\n=== SDELKI S SENTIMENT (vsego {len(sent_trades)}) ===")
    print(f"  Pribylnykh: {len(positive)}, Ubytochnykh: {len(negative)}")

    if positive:
        print("  Gde sentiment POMOG:")
        for t in sorted(positive, key=lambda x: x.net_pnl, reverse=True)[:3]:
            print(f"    {t.direction} {t.entry_date} sent={t.sentiment_used:+.2f} "
                  f"PnL={t.net_pnl:+,.0f}")

    if negative:
        print("  Gde sentiment NE pomog:")
        for t in sorted(negative, key=lambda x: x.net_pnl)[:3]:
            print(f"    {t.direction} {t.entry_date} sent={t.sentiment_used:+.2f} "
                  f"PnL={t.net_pnl:+,.0f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(description="USDRUB Backtest with Claude + Sentiment")
    parser.add_argument("--skip-claude", action="store_true",
                        help="Run algo-only, no Claude API calls")
    parser.add_argument("--use-cache", action="store_true",
                        help="Use only cached Claude responses")
    parser.add_argument("--no-live", action="store_true",
                        help="Skip live RSS news test")
    args = parser.parse_args()

    init_cache(DB_PATH)

    print("=" * 75)
    print("  BACKTEST USDRUB + CLAUDE + NOVOSTI (2024-2026)")
    print(f"  Instrument: {TICKER}")
    print(f"  Kapital:    {INITIAL_CAPITAL:,.0f} RUB")
    print(f"  Period:     {START_DATE} -- {END_DATE}")
    print(f"  Resheniya:  kazhdyj ponedelnik")
    print("=" * 75)

    # Load data
    log.info("loading_data")
    candles = load_usdrub_candles(DB_PATH)
    log.info("data_loaded", ticker=TICKER, bars=len(candles),
             first=str(candles[0].dt), last=str(candles[-1].dt))

    df = candles_to_df(candles)
    df = add_indicators(df)
    rows = df.to_dicts()
    date_to_idx = {r["date"]: i for i, r in enumerate(rows)}

    mondays = get_mondays(START_DATE, END_DATE)
    log.info("decision_points", mondays=len(mondays))

    # --- Variant A: Algo only ---
    variant_a = await run_variant(
        name="A: Algo (bez Claude)",
        rows=rows, date_to_idx=date_to_idx, mondays=mondays,
        candles=candles, capital=INITIAL_CAPITAL,
        use_claude=False, use_sentiment=False,
        use_cache_only=False,
    )

    variant_b = None
    variant_c = None
    variant_d = None

    if not args.skip_claude:
        # --- Variant B: Claude WITHOUT sentiment ---
        variant_b = await run_variant(
            name="B: Claude bez sentiment",
            rows=rows, date_to_idx=date_to_idx, mondays=mondays,
            candles=candles, capital=INITIAL_CAPITAL,
            use_claude=True, use_sentiment=False,
            use_cache_only=args.use_cache,
        )

        # --- Variant C: Claude WITH synthetic sentiment ---
        variant_c = await run_variant(
            name="C: Claude + synth sentiment",
            rows=rows, date_to_idx=date_to_idx, mondays=mondays,
            candles=candles, capital=INITIAL_CAPITAL,
            use_claude=True, use_sentiment=True,
            use_cache_only=args.use_cache,
        )

        # --- Variant D: Live RSS news (last 2 weeks) ---
        if not args.no_live:
            log.info("fetching_live_news")
            try:
                live_articles = await fetch_live_news_sentiment()
                if live_articles:
                    live_score, scored_articles = await score_news_sentiment_claude(live_articles)
                    log.info("live_sentiment", score=live_score, articles=len(scored_articles))
                else:
                    live_score = 0.0
                    scored_articles = []
            except Exception as exc:
                log.warning("live_news_error", error=str(exc))
                live_score = 0.0
                scored_articles = []

            live_start = END_DATE - timedelta(days=14)
            live_mondays = [m for m in mondays if m >= live_start]

            if live_mondays:
                variant_d = await run_variant(
                    name="D: Claude + live RSS news",
                    rows=rows, date_to_idx=date_to_idx, mondays=live_mondays,
                    candles=candles, capital=INITIAL_CAPITAL,
                    use_claude=True, use_sentiment=True,
                    use_cache_only=args.use_cache,
                    live_sentiment_score=live_score,
                    live_news_start=live_start,
                )

    # --- Print results ---
    print("\n" + "=" * 75)
    print("  REZULTATY BACKTESTA USDRUB + CLAUDE + NOVOSTI (2024-2026)")
    print("=" * 75)

    all_variants = [variant_a]
    print_variant(variant_a)

    if variant_b:
        print_variant(variant_b)
        all_variants.append(variant_b)

    if variant_c:
        print_variant(variant_c)
        all_variants.append(variant_c)

    if variant_d:
        print_variant(variant_d)
        all_variants.append(variant_d)

    # Comparison table
    print_comparison_table(all_variants)

    # Sentiment effect
    if variant_b and variant_c:
        print_sentiment_effect(variant_b, variant_c)

    # Trade examples
    if variant_b:
        print_trade_examples(variant_b, "B: bez sentiment")
    if variant_c:
        print_trade_examples(variant_c, "C: s sentiment")
        print_sentiment_examples(variant_c)

    # Live test results
    if variant_d:
        print(f"\n=== LIVE TEST (poslednie 2 nedeli) ===")
        print(f"  Period: {END_DATE - timedelta(days=14)} -- {END_DATE}")
        print_variant(variant_d)
        if 'scored_articles' in dir() and scored_articles:
            print(f"  Realnye novosti ispolzovany: {len(scored_articles)}")
            print("  Primery:")
            for sa in scored_articles[:5]:
                print(f"    \"{sa['title']}\" -> sentiment {sa['score']:+.2f} ({sa.get('reason', '')})")

    # Exit reasons stats
    print("\n=== STATISTIKA PO PRICHNAM VYKHODA ===")
    for v in all_variants:
        reasons: dict[str, int] = {}
        for t in v.trades:
            reasons[t.exit_reason] = reasons.get(t.exit_reason, 0) + 1
        if reasons:
            reasons_str = ", ".join(f"{k}={v}" for k, v in sorted(reasons.items()))
            print(f"  {v.name}: {reasons_str}")

    # Cost summary
    total_cost = sum(v.claude_cost_usd for v in all_variants if v)
    if total_cost > 0:
        print(f"\n=== STOIMOST CLAUDE API ===")
        for v in all_variants:
            if v and v.claude_calls > 0:
                print(f"  {v.name}: {v.claude_calls} calls, "
                      f"in={v.claude_input_tokens:,} tok, "
                      f"out={v.claude_output_tokens:,} tok, "
                      f"${v.claude_cost_usd:.4f}")
        print(f"  ITOGO: ${total_cost:.4f}")

    # Cache stats
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT model, COUNT(*) FROM claude_cache "
        "WHERE ticker LIKE 'USDRUB%' GROUP BY model"
    )
    cache_stats = cur.fetchall()
    conn.close()
    if cache_stats:
        print(f"\n=== KESH CLAUDE (USDRUB) ===")
        for model_name, cnt in cache_stats:
            print(f"  {model_name}: {cnt} zapisej")

    print("\n" + "=" * 75)
    print("  DONE")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())
