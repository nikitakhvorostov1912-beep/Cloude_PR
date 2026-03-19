"""Walk-Forward Optimization for MOEX Trading System.

Methodology:
  6 windows, Train=2.5yr, Test=6mo, Step=6mo
  Random Search (50 samples from PARAM_GRID) on Train
  Best params by Sharpe -> applied on Test (OOS)
  Aggregate OOS Sharpe reported + overfitting check

Tickers: SBER, GAZP, LKOH (3 most liquid)
No Claude API calls - pure algorithmic backtest.

Usage: python -m scripts.walk_forward_optimize
"""

from __future__ import annotations

import asyncio
import math
import random
import statistics
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import polars as pl
import structlog

from src.analysis.features import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger,
    calculate_ema,
    calculate_macd,
    calculate_obv,
    calculate_rsi,
    calculate_volume_ratio,
)
from src.analysis.scoring import calculate_pre_score
from src.data.db import get_candles
from src.models.market import OHLCVBar
from src.risk.position_sizer import (
    calculate_consecutive_multiplier,
    calculate_drawdown_multiplier,
)

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(colors=False),
    ],
)
log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

DB_PATH = "data/trading.db"
WF_TICKERS = ["SBER", "GAZP", "LKOH"]
RANDOM_SEARCH_N = 50
INITIAL_CAPITAL = 1_000_000.0
RISK_PER_TRADE = 0.015
MAX_POSITION_PCT = 0.15
COMMISSION_RT = 0.002

# MR exit thresholds (фиксированные, не оптимизируются)
MR_RSI2_EXIT_LONG = 70.0
MR_RSI2_EXIT_SHORT = 30.0
MR_HOLD_DAYS = 5

TICKER_META: dict[str, dict] = {
    "SBER": {"sector": "banks",   "lot_size": 1},
    "GAZP": {"sector": "oil_gas", "lot_size": 10},
    "LKOH": {"sector": "oil_gas", "lot_size": 1},
}

# Параметры по умолчанию (из run_enhanced_backtest.py)
DEFAULT_PARAMS: dict[str, float | int] = {
    "rsi_buy_threshold":   48,
    "rsi_sell_threshold":  70,
    "adx_trend_threshold": 25,
    "atr_stop_mult":       2.5,
    "pre_score_threshold": 55,
    "rsi2_mr_buy":         10,
    "rsi2_mr_sell":        90,
    "time_stop_days":      30,
}

PARAM_GRID: dict[str, list] = {
    "rsi_buy_threshold":   [30, 35, 40],
    "rsi_sell_threshold":  [65, 70, 75],
    "adx_trend_threshold": [20, 25, 30],
    "atr_stop_mult":       [2.0, 2.5, 3.0],
    "pre_score_threshold": [45, 55, 65],
    "rsi2_mr_buy":         [5, 10, 15],
    "rsi2_mr_sell":        [85, 90, 95],
    "time_stop_days":      [15, 20, 30],
}

# Walk-Forward окна
WF_WINDOWS = [
    {"train_start": date(2021, 1, 1),  "train_end": date(2023, 6, 30),
     "test_start":  date(2023, 7, 1),  "test_end":  date(2023, 12, 31)},
    {"train_start": date(2021, 7, 1),  "train_end": date(2024, 1, 31),
     "test_start":  date(2024, 1, 1),  "test_end":  date(2024, 6, 30)},
    {"train_start": date(2022, 1, 1),  "train_end": date(2024, 6, 30),
     "test_start":  date(2024, 7, 1),  "test_end":  date(2024, 12, 31)},
    {"train_start": date(2022, 7, 1),  "train_end": date(2025, 1, 31),
     "test_start":  date(2025, 1, 1),  "test_end":  date(2025, 6, 30)},
    {"train_start": date(2023, 1, 1),  "train_end": date(2025, 6, 30),
     "test_start":  date(2025, 7, 1),  "test_end":  date(2025, 12, 31)},
    {"train_start": date(2023, 7, 1),  "train_end": date(2026, 1, 31),
     "test_start":  date(2026, 1, 1),  "test_end":  date(2026, 3, 18)},
]


# ---------------------------------------------------------------------------
# Структуры данных (копия из run_enhanced_backtest.py)
# ---------------------------------------------------------------------------

@dataclass
class Position:
    ticker: str
    direction: str
    strategy: str
    entry_price: float
    entry_date: date
    entry_idx: int
    lots: int
    lot_size: int
    stop_loss: float
    trail_stop: float
    tp1_price: float
    tp2_price: float
    tp1_done: bool = False
    tp2_done: bool = False
    peak_price: float = 0.0


@dataclass
class TradeRecord:
    ticker: str
    pnl: float
    pnl_pct: float


# ---------------------------------------------------------------------------
# DataFrame + индикаторы
# ---------------------------------------------------------------------------

def build_dataframe(candles: list[OHLCVBar]) -> pl.DataFrame:
    df = pl.DataFrame({
        "date":   [c.dt for c in candles],
        "open":   [c.open for c in candles],
        "high":   [c.high for c in candles],
        "low":    [c.low for c in candles],
        "close":  [c.close for c in candles],
        "volume": [c.volume for c in candles],
    }).sort("date")
    return df


def add_indicators(df: pl.DataFrame) -> pl.DataFrame:
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    volume = df["volume"]

    ema20  = calculate_ema(close, 20)
    ema50  = calculate_ema(close, 50)
    ema200 = calculate_ema(close, 200)
    rsi14  = calculate_rsi(close, 14)
    rsi2   = calculate_rsi(close, 2)
    macd_d = calculate_macd(close)
    adx_d  = calculate_adx(high, low, close, 14)
    bb_d   = calculate_bollinger(close, 20, 2.0)
    atr14  = calculate_atr(high, low, close, 14)
    obv    = calculate_obv(close, volume)
    vol_ratio = calculate_volume_ratio(volume, 20)

    close_pd = close.to_pandas()
    z_mean = close_pd.rolling(20, min_periods=5).mean()
    z_std  = close_pd.rolling(20, min_periods=5).std()
    z_score = (close_pd - z_mean) / z_std.replace(0, float("nan"))
    z_series = pl.Series(name="z_score", values=z_score.values)

    return df.with_columns([
        ema20.alias("ema_20"),
        ema50.alias("ema_50"),
        ema200.alias("ema_200"),
        rsi14.alias("rsi_14"),
        rsi2.alias("rsi_2"),
        macd_d["histogram"].alias("macd_hist"),
        adx_d["adx"].alias("adx"),
        adx_d["di_plus"].alias("di_plus"),
        adx_d["di_minus"].alias("di_minus"),
        bb_d["bb_upper"].alias("bb_upper"),
        bb_d["bb_lower"].alias("bb_lower"),
        atr14.alias("atr"),
        obv.alias("obv"),
        vol_ratio.alias("vol_ratio"),
        z_series,
    ])


def filter_period(df: pl.DataFrame, start: date, end: date) -> pl.DataFrame:
    return df.filter(
        (pl.col("date") >= start) & (pl.col("date") <= end)
    )


# ---------------------------------------------------------------------------
# Режим рынка
# ---------------------------------------------------------------------------

def get_regime(row: dict, adx_thresh: float) -> str:
    adx   = row.get("adx") or 0.0
    close = row.get("close") or 0.0
    ema200 = row.get("ema_200") or 0.0
    atr   = row.get("atr") or 0.0

    atr_pct = atr / close if close > 0 else 0.0
    if atr_pct > 0.035:
        return "crisis"

    if adx > adx_thresh:
        return "uptrend" if close > ema200 else "downtrend"

    if adx < (adx_thresh - 5):
        return "range"

    return "weak_trend"


def obv_trend(obv_history: list[float], window: int = 5) -> str:
    if len(obv_history) < window:
        return "flat"
    recent = obv_history[-window:]
    if recent[-1] > recent[0] * 1.01:
        return "up"
    if recent[-1] < recent[0] * 0.99:
        return "down"
    return "flat"


# ---------------------------------------------------------------------------
# Pre-Score
# ---------------------------------------------------------------------------

def compute_pre_score(row: dict, direction: str, obv_tr: str) -> float:
    adx      = row.get("adx") or 0.0
    di_plus  = row.get("di_plus") or 0.0
    di_minus = row.get("di_minus") or 0.0
    rsi      = row.get("rsi_14") or 50.0
    macd_hist = row.get("macd_hist") or 0.0
    close    = row.get("close") or 1.0
    ema20    = row.get("ema_20") or close
    ema50    = row.get("ema_50") or close
    ema200   = row.get("ema_200") or close
    vol_ratio = row.get("vol_ratio") or 1.0

    score, _ = calculate_pre_score(
        adx=adx, di_plus=di_plus, di_minus=di_minus,
        rsi=rsi, macd_hist=macd_hist, close=close,
        ema20=ema20, ema50=ema50, ema200=ema200,
        volume_ratio=vol_ratio, obv_trend=obv_tr,
        sentiment_score=0.0, direction=direction,
    )
    return score


# ---------------------------------------------------------------------------
# Размер позиции
# ---------------------------------------------------------------------------

def calc_lot_size(
    equity: float,
    entry_price: float,
    stop_distance: float,
    lot_size: int,
    direction: str,
    drawdown: float,
    consecutive_losses: int,
) -> tuple[int, float]:
    if stop_distance <= 0 or entry_price <= 0 or equity <= 0:
        return 0, 0.0

    dd_mult   = calculate_drawdown_multiplier(drawdown)
    cons_mult = calculate_consecutive_multiplier(consecutive_losses)
    effective_risk = RISK_PER_TRADE * dd_mult * cons_mult
    if effective_risk <= 0:
        return 0, 0.0

    risk_amount    = equity * effective_risk
    shares_by_risk = risk_amount / stop_distance
    position_value = shares_by_risk * entry_price
    position_value = min(position_value, equity * MAX_POSITION_PCT)

    if direction == "short":
        position_value *= 0.6

    value_per_lot = entry_price * lot_size
    if value_per_lot <= 0:
        return 0, 0.0

    lots = math.floor(position_value / value_per_lot)
    return lots, lots * value_per_lot


# ---------------------------------------------------------------------------
# Бэктест одного тикера с параметрами
# ---------------------------------------------------------------------------

def backtest_ticker_params(
    ticker: str,
    df: pl.DataFrame,
    params: dict,
    initial_equity: float,
    lot_size: int,
) -> list[TradeRecord]:
    """Запускает бэктест тикера с заданными параметрами, возвращает список сделок."""
    rsi_buy_thr   = float(params["rsi_buy_threshold"])
    adx_thresh    = float(params["adx_trend_threshold"])
    atr_stop_mult = float(params["atr_stop_mult"])
    pre_score_thr = float(params["pre_score_threshold"])
    rsi2_mr_buy   = float(params["rsi2_mr_buy"])
    rsi2_mr_sell  = float(params["rsi2_mr_sell"])
    time_stop_d   = int(params["time_stop_days"])

    atr_tp1 = 2.0
    atr_tp2 = 3.5

    trades: list[TradeRecord] = []
    position: Optional[Position] = None
    equity = initial_equity
    peak_equity = equity
    obv_history: list[float] = []
    consecutive_losses = 0

    rows = df.to_dicts()

    for i, row in enumerate(rows):
        close  = row.get("close") or 0.0
        high   = row.get("high") or close
        low    = row.get("low") or close
        atr    = row.get("atr") or 0.0
        rsi14  = row.get("rsi_14")
        rsi2   = row.get("rsi_2")
        ema200 = row.get("ema_200")
        ema50  = row.get("ema_50")
        macd_hist = row.get("macd_hist")
        adx    = row.get("adx")
        bb_upper = row.get("bb_upper")
        bb_lower = row.get("bb_lower")
        z_score  = row.get("z_score")
        vol_ratio = row.get("vol_ratio")
        obv_val  = row.get("obv")
        dt = row["date"]

        if obv_val is not None:
            obv_history.append(obv_val)

        required = [rsi14, rsi2, ema200, ema50, macd_hist, adx, atr, bb_upper, bb_lower]
        if any(v is None or (isinstance(v, float) and v != v) for v in required):
            continue
        if atr <= 0 or close <= 0:
            continue

        regime = get_regime(row, adx_thresh)
        obv_tr = obv_trend(obv_history)
        drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0

        # --- EXIT ---
        if position is not None:
            days_held = i - position.entry_idx
            pos = position
            exit_price: Optional[float] = None
            exit_reason: Optional[str] = None

            if regime == "crisis":
                exit_price = close
                exit_reason = "crisis"

            elif pos.direction == "short":
                if high >= pos.stop_loss:
                    exit_price = pos.stop_loss
                    exit_reason = "stop_loss"
                elif pos.strategy == "mr_short" and rsi2 < MR_RSI2_EXIT_SHORT:
                    exit_price = close
                    exit_reason = "mr_exit"
                elif pos.strategy == "mr_short" and days_held >= MR_HOLD_DAYS:
                    exit_price = close
                    exit_reason = "time_mr"
                else:
                    if close < pos.peak_price:
                        pos.peak_price = close
                        pos.trail_stop = pos.peak_price + atr * atr_stop_mult
                    if high >= pos.trail_stop:
                        exit_price = pos.trail_stop
                        exit_reason = "trailing"

            else:
                # Обновить трейлинг
                if high > pos.peak_price:
                    pos.peak_price = high
                    new_trail = pos.peak_price - atr * atr_stop_mult
                    pos.trail_stop = max(pos.trail_stop, new_trail)

                # TP1
                if not pos.tp1_done and high >= pos.tp1_price:
                    tp_lots = max(1, math.floor(pos.lots * 0.30))
                    pnl = (pos.tp1_price - pos.entry_price) * tp_lots * pos.lot_size
                    pnl -= pos.entry_price * tp_lots * pos.lot_size * COMMISSION_RT
                    equity += pnl
                    pos.lots -= tp_lots
                    pos.tp1_done = True
                    trades.append(TradeRecord(ticker=ticker, pnl=round(pnl, 2),
                                              pnl_pct=round((pos.tp1_price / pos.entry_price - 1) * 100, 2)))
                    consecutive_losses = 0 if pnl > 0 else consecutive_losses + 1

                # TP2
                if pos.tp1_done and not pos.tp2_done and high >= pos.tp2_price:
                    tp_lots = max(1, math.floor(pos.lots * 0.43))
                    pnl = (pos.tp2_price - pos.entry_price) * tp_lots * pos.lot_size
                    pnl -= pos.entry_price * tp_lots * pos.lot_size * COMMISSION_RT
                    equity += pnl
                    pos.lots -= tp_lots
                    pos.tp2_done = True
                    trades.append(TradeRecord(ticker=ticker, pnl=round(pnl, 2),
                                              pnl_pct=round((pos.tp2_price / pos.entry_price - 1) * 100, 2)))

                if exit_price is None and low <= pos.trail_stop:
                    exit_price = pos.trail_stop
                    exit_reason = "trailing"

                if exit_price is None and low <= pos.stop_loss:
                    exit_price = pos.stop_loss
                    exit_reason = "stop_loss"

                if exit_price is None and pos.strategy == "mean_reversion" and rsi2 > MR_RSI2_EXIT_LONG:
                    exit_price = close
                    exit_reason = "mr_exit"

                if exit_price is None and pos.strategy == "mean_reversion" and days_held >= MR_HOLD_DAYS:
                    exit_price = close
                    exit_reason = "time_mr"

                if exit_price is None and pos.strategy == "trend" and close < ema50 and adx > adx_thresh * 0.8:
                    exit_price = close
                    exit_reason = "ema50_break"

                if exit_price is None and regime == "downtrend":
                    exit_price = close
                    exit_reason = "regime_down"

                if exit_price is None and days_held >= time_stop_d:
                    growth = (close - pos.entry_price) / pos.entry_price
                    if growth < 0.10:
                        exit_price = close
                        exit_reason = "time_stop"

                if exit_price is None and days_held >= 15:
                    if close <= pos.entry_price:
                        exit_price = close
                        exit_reason = "time_15d"

            if exit_price is not None and exit_reason is not None and pos.lots > 0:
                mult = -1 if pos.direction == "short" else 1
                pnl = mult * (exit_price - pos.entry_price) * pos.lots * pos.lot_size
                pnl -= pos.entry_price * pos.lots * pos.lot_size * COMMISSION_RT
                equity += pnl
                if pnl > 0:
                    consecutive_losses = 0
                else:
                    consecutive_losses += 1
                trades.append(TradeRecord(ticker=ticker, pnl=round(pnl, 2),
                                          pnl_pct=round(mult * (exit_price / pos.entry_price - 1) * 100, 2)))
                position = None

        # --- ENTRY ---
        if position is None and regime not in ("crisis", "downtrend"):

            if regime in ("uptrend", "weak_trend"):
                pre_score = compute_pre_score(row, "long", obv_tr)
                buy_signal = (
                    pre_score >= pre_score_thr
                    and rsi14 < rsi_buy_thr
                    and (macd_hist or 0.0) > 0
                    and close > ema50
                    and (vol_ratio or 0.0) > 0.7
                )
                if buy_signal:
                    stop_dist = atr * atr_stop_mult
                    lots, _ = calc_lot_size(equity, close, stop_dist, lot_size,
                                            "long", drawdown, consecutive_losses)
                    if lots > 0:
                        position = Position(
                            ticker=ticker, direction="long", strategy="trend",
                            entry_price=close, entry_date=dt, entry_idx=i,
                            lots=lots, lot_size=lot_size,
                            stop_loss=close - stop_dist,
                            trail_stop=close - stop_dist,
                            tp1_price=close + atr * atr_tp1,
                            tp2_price=close + atr * atr_tp2,
                            peak_price=close,
                        )

            elif regime == "range" and rsi2 is not None:
                if (rsi2 < rsi2_mr_buy and close > ema200 and close < (bb_lower or 0.0)):
                    stop_dist = atr * atr_stop_mult
                    lots, _ = calc_lot_size(equity, close, stop_dist, lot_size,
                                            "long", drawdown, consecutive_losses)
                    if lots > 0:
                        position = Position(
                            ticker=ticker, direction="long", strategy="mean_reversion",
                            entry_price=close, entry_date=dt, entry_idx=i,
                            lots=lots, lot_size=lot_size,
                            stop_loss=close - stop_dist,
                            trail_stop=close - stop_dist,
                            tp1_price=close + atr * atr_tp1,
                            tp2_price=close + atr * atr_tp2,
                            peak_price=close,
                        )
                elif (rsi2 > rsi2_mr_sell and close < ema200
                      and close > (bb_upper or float("inf"))
                      and (z_score or 0.0) > 2.0):
                    stop_dist = atr * atr_stop_mult
                    short_stop = close + stop_dist
                    lots, _ = calc_lot_size(equity, close, stop_dist, lot_size,
                                            "short", drawdown, consecutive_losses)
                    if lots > 0:
                        position = Position(
                            ticker=ticker, direction="short", strategy="mr_short",
                            entry_price=close, entry_date=dt, entry_idx=i,
                            lots=lots, lot_size=lot_size,
                            stop_loss=short_stop, trail_stop=short_stop,
                            tp1_price=close - atr * atr_tp1,
                            tp2_price=close - atr * atr_tp2,
                            peak_price=close,
                        )

        if equity > peak_equity:
            peak_equity = equity

    # Закрыть открытую позицию по последней цене
    if position is not None and rows:
        last = rows[-1]
        last_close = last["close"]
        mult = -1 if position.direction == "short" else 1
        pnl = mult * (last_close - position.entry_price) * position.lots * position.lot_size
        pnl -= position.entry_price * position.lots * position.lot_size * COMMISSION_RT
        equity += pnl
        trades.append(TradeRecord(ticker=ticker, pnl=round(pnl, 2),
                                  pnl_pct=round(mult * (last_close / position.entry_price - 1) * 100, 2)))

    return trades


# ---------------------------------------------------------------------------
# Метрики
# ---------------------------------------------------------------------------

def calc_sharpe(trades: list[TradeRecord], n_years: float = 1.0) -> float:
    """Annualised Sharpe ratio по трейдам."""
    if len(trades) < 3:
        return 0.0
    rets = [t.pnl_pct / 100.0 for t in trades]
    mean_r = statistics.mean(rets)
    try:
        std_r = statistics.stdev(rets)
    except statistics.StatisticsError:
        return 0.0
    if std_r == 0:
        return 0.0
    avg_trades_per_year = len(trades) / max(n_years, 0.1)
    rf_per_trade = 0.10 / avg_trades_per_year if avg_trades_per_year > 0 else 0.0
    return round((mean_r - rf_per_trade) / std_r * math.sqrt(avg_trades_per_year), 3)


def calc_return_pct(trades: list[TradeRecord], initial_equity: float) -> float:
    if initial_equity <= 0:
        return 0.0
    total_pnl = sum(t.pnl for t in trades)
    return round(total_pnl / initial_equity * 100, 2)


# ---------------------------------------------------------------------------
# Backtest по всем тикерам + периоду
# ---------------------------------------------------------------------------

async def run_portfolio_backtest(
    all_dfs: dict[str, pl.DataFrame],
    params: dict,
    start: date,
    end: date,
    n_years: float,
) -> tuple[float, float, list[TradeRecord]]:
    """
    Запускает бэктест для WF_TICKERS на заданном периоде с params.
    Возвращает (sharpe, return_pct, all_trades).
    """
    all_trades: list[TradeRecord] = []
    capital_per_ticker = INITIAL_CAPITAL / len(WF_TICKERS)

    for ticker in WF_TICKERS:
        full_df = all_dfs.get(ticker)
        if full_df is None:
            continue
        df = filter_period(full_df, start, end)
        if len(df) < 50:
            continue
        lot_size = TICKER_META[ticker]["lot_size"]
        trades = backtest_ticker_params(ticker, df, params, capital_per_ticker, lot_size)
        all_trades.extend(trades)

    sharpe = calc_sharpe(all_trades, n_years)
    ret_pct = calc_return_pct(all_trades, INITIAL_CAPITAL)
    return sharpe, ret_pct, all_trades


# ---------------------------------------------------------------------------
# Random Search по PARAM_GRID
# ---------------------------------------------------------------------------

def sample_params(n: int, seed: int = 42) -> list[dict]:
    """Случайная выборка n комбинаций из PARAM_GRID."""
    rng = random.Random(seed)
    keys = list(PARAM_GRID.keys())
    sampled = set()
    result = []

    # Всего возможных комбинаций
    total = 1
    for v in PARAM_GRID.values():
        total *= len(v)

    attempts = 0
    max_attempts = n * 20

    while len(result) < n and attempts < max_attempts:
        combo = tuple(rng.choice(PARAM_GRID[k]) for k in keys)
        if combo not in sampled:
            sampled.add(combo)
            result.append(dict(zip(keys, combo)))
        attempts += 1

    return result


# ---------------------------------------------------------------------------
# Главная функция Walk-Forward
# ---------------------------------------------------------------------------

async def main() -> None:
    log.info("walk_forward_start",
             tickers=WF_TICKERS,
             windows=len(WF_WINDOWS),
             random_search_n=RANDOM_SEARCH_N)

    # --- Загрузка всех данных заранее ---
    log.info("loading_data")
    all_dfs: dict[str, pl.DataFrame] = {}
    full_start = date(2021, 1, 1)
    full_end   = date(2026, 3, 18)

    for ticker in WF_TICKERS:
        candles = await get_candles(DB_PATH, ticker, full_start, full_end)
        if len(candles) < 220:
            log.warning("insufficient_data", ticker=ticker, bars=len(candles))
            continue
        df = build_dataframe(candles)
        df = add_indicators(df)
        all_dfs[ticker] = df
        log.info("data_loaded", ticker=ticker, bars=len(df))

    if not all_dfs:
        log.error("no_data_available")
        return

    # --- Random Search параметры ---
    param_candidates = sample_params(RANDOM_SEARCH_N)
    log.info("param_candidates_generated", n=len(param_candidates))

    # --- Walk-Forward ---
    window_results = []
    all_oos_trades: list[TradeRecord] = []

    for win_idx, window in enumerate(WF_WINDOWS):
        train_start = window["train_start"]
        train_end   = window["train_end"]
        test_start  = window["test_start"]
        test_end    = window["test_end"]

        train_years = (train_end - train_start).days / 365.25
        test_years  = (test_end  - test_start).days  / 365.25

        log.info(
            "window_start",
            window=win_idx + 1,
            train=f"{train_start} .. {train_end}",
            test=f"{test_start} .. {test_end}",
        )

        # --- IS: Grid Search на Train ---
        best_is_sharpe = -999.0
        best_params = param_candidates[0]
        best_is_ret  = 0.0

        for p_idx, params in enumerate(param_candidates):
            is_sharpe, is_ret, _ = await run_portfolio_backtest(
                all_dfs, params, train_start, train_end, train_years
            )
            if is_sharpe > best_is_sharpe:
                best_is_sharpe = is_sharpe
                best_params = params
                best_is_ret = is_ret

        log.info(
            "train_best_found",
            window=win_idx + 1,
            sharpe=f"{best_is_sharpe:.3f}",
            ret=f"{best_is_ret:+.2f}%",
            params=best_params,
        )

        # --- OOS: Test с лучшими параметрами ---
        oos_sharpe, oos_ret, oos_trades = await run_portfolio_backtest(
            all_dfs, best_params, test_start, test_end, test_years
        )
        all_oos_trades.extend(oos_trades)

        log.info(
            "test_result",
            window=win_idx + 1,
            oos_sharpe=f"{oos_sharpe:.3f}",
            oos_ret=f"{oos_ret:+.2f}%",
            oos_trades=len(oos_trades),
        )

        window_results.append({
            "window": win_idx + 1,
            "train_start": train_start,
            "test_start":  test_start,
            "test_end":    test_end,
            "is_sharpe":   best_is_sharpe,
            "is_ret":      best_is_ret,
            "oos_sharpe":  oos_sharpe,
            "oos_ret":     oos_ret,
            "best_params": best_params,
        })

    # ---------------------------------------------------------------------------
    # Aggregate OOS
    # ---------------------------------------------------------------------------
    full_oos_years = (WF_WINDOWS[-1]["test_end"] - WF_WINDOWS[0]["test_start"]).days / 365.25
    aggregate_oos_sharpe = calc_sharpe(all_oos_trades, full_oos_years)
    aggregate_oos_ret    = calc_return_pct(all_oos_trades, INITIAL_CAPITAL)

    # ---------------------------------------------------------------------------
    # Default params baseline (весь период)
    # ---------------------------------------------------------------------------
    log.info("running_default_baseline")
    def_sharpe, def_ret, _ = await run_portfolio_backtest(
        all_dfs, DEFAULT_PARAMS,
        full_start, full_end,
        (full_end - full_start).days / 365.25,
    )

    # ---------------------------------------------------------------------------
    # Overfitting Check
    # ---------------------------------------------------------------------------
    valid_windows = [w for w in window_results if w["oos_sharpe"] != 0 and w["is_sharpe"] != 0]
    if valid_windows:
        avg_is  = statistics.mean(w["is_sharpe"] for w in valid_windows)
        avg_oos = statistics.mean(w["oos_sharpe"] for w in valid_windows)
        is_oos_ratio = abs(avg_is / avg_oos) if avg_oos != 0 else float("inf")
    else:
        avg_is = avg_oos = is_oos_ratio = 0.0

    overfit_ok = is_oos_ratio < 2.0

    # Параметрическая стабильность: насколько часто один и тот же параметр выигрывает
    param_frequency: dict[str, dict] = {}
    for w in window_results:
        for k, v in w["best_params"].items():
            if k not in param_frequency:
                param_frequency[k] = {}
            param_frequency[k][str(v)] = param_frequency[k].get(str(v), 0) + 1

    # Лучший набор параметров по частоте (majority vote)
    best_params_voted: dict = {}
    for k, freq in param_frequency.items():
        best_val_str = max(freq, key=lambda x: freq[x])
        # Восстановить тип из PARAM_GRID
        grid_vals = PARAM_GRID[k]
        try:
            best_val = type(grid_vals[0])(best_val_str)
        except (ValueError, TypeError):
            best_val = best_val_str
        best_params_voted[k] = best_val

    param_sensitivity_ok = all(
        max(freq.values()) >= len(WF_WINDOWS) // 2
        for freq in param_frequency.values()
    )

    # ---------------------------------------------------------------------------
    # Вывод результатов
    # ---------------------------------------------------------------------------
    sep = "=" * 60
    print()
    print(sep)
    print("  Walk-Forward Optimization Results")
    print(sep)
    print()

    for w in window_results:
        print(
            f"  Window {w['window']:d}: "
            f"Train [{w['train_start']} .. {w['test_start'] - timedelta(days=1)}] "
            f"Sharpe={w['is_sharpe']:+.3f} ({w['is_ret']:+.1f}%)  |  "
            f"Test [{w['test_start']} .. {w['test_end']}] "
            f"OOS Sharpe={w['oos_sharpe']:+.3f} ({w['oos_ret']:+.1f}%)"
        )

    print()
    print(f"  Aggregate OOS Sharpe : {aggregate_oos_sharpe:+.3f}")
    print(f"  Aggregate OOS Return : {aggregate_oos_ret:+.2f}%")
    print()
    print(f"  Best Parameters (majority vote):")
    for k, v in best_params_voted.items():
        default_v = DEFAULT_PARAMS.get(k, "?")
        marker = " <-- changed" if v != default_v else ""
        print(f"    {k:28s} = {str(v):6s}  (default={default_v}){marker}")

    print()
    print(sep)
    print("  Comparison: Default vs Optimized")
    print(sep)
    print(f"  Default params  : Sharpe={def_sharpe:+.3f}, Return={def_ret:+.2f}%")
    print(f"  Optimized (OOS) : Sharpe={aggregate_oos_sharpe:+.3f}, Return={aggregate_oos_ret:+.2f}%")
    delta_sharpe = aggregate_oos_sharpe - def_sharpe
    delta_ret    = aggregate_oos_ret    - def_ret
    print(f"  Improvement     : Sharpe {delta_sharpe:+.3f}, Return {delta_ret:+.2f}pp")

    print()
    print(sep)
    print("  Overfitting Check")
    print(sep)
    print(f"  Avg IS Sharpe       : {avg_is:+.3f}")
    print(f"  Avg OOS Sharpe      : {avg_oos:+.3f}")
    print(f"  IS/OOS Ratio        : {is_oos_ratio:.2f}  (< 2.0 = OK)")
    print(f"  Overfit Status      : {'PASS' if overfit_ok else 'FAIL - possible overfit'}")
    print(f"  Param Sensitivity   : {'PASS' if param_sensitivity_ok else 'FAIL - unstable'}")

    print()

    # Детальная частота параметров
    print(sep)
    print("  Parameter Frequency Across Windows")
    print(sep)
    for k, freq in param_frequency.items():
        freq_str = "  ".join(f"{v}:{cnt}" for v, cnt in sorted(freq.items()))
        print(f"  {k:28s}: {freq_str}")

    print()
    print(sep)
    print()


if __name__ == "__main__":
    asyncio.run(main())
