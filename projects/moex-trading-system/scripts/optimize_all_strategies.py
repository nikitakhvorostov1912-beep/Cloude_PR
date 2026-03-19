"""Оптимизация параметров всех стратегий — Random Search + Walk-Forward.

Стратегии:
- Trend Following (RSI + ADX + EMA + ATR)
- Mean Reversion (RSI2 + Bollinger Bands + Time Stop)
- Pairs Trading (Z-score: SBER/VTBR)

Два периода:
- "Без кризиса": 2023-01-01 — 2026-03-18
- "Полный":      2021-01-01 — 2026-03-18

Запуск: python -m scripts.optimize_all_strategies
"""

from __future__ import annotations

import asyncio
import math
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import polars as pl

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
from src.data.db import get_candles
from src.models.market import OHLCVBar

DB_PATH = "data/trading.db"
INITIAL_CAPITAL = 1_000_000.0
COMMISSION_RT = 0.002
RANDOM_SEED = 42
N_COMBINATIONS = 30

TREND_PARAMS = {
    "rsi_buy":       [30, 35, 40, 45],
    "rsi_sell":      [60, 65, 70, 75],
    "adx_threshold": [15, 20, 25, 30],
    "atr_stop_mult": [2.0, 2.5, 3.0, 3.5],
    "ema_fast":      [10, 20, 30],
    "ema_slow":      [50, 100],
}

MR_PARAMS = {
    "rsi2_buy":  [3, 5, 10, 15],
    "rsi2_sell": [85, 90, 95],
    "time_stop": [3, 5, 7, 10],
    "bb_period": [15, 20, 25],
    "bb_std":    [1.5, 2.0, 2.5],
}

PAIRS_PARAMS = {
    "lookback":    [30, 60, 90, 120],
    "entry_zscore": [1.5, 2.0, 2.5],
    "exit_zscore":  [0.0, 0.25, 0.5],
    "stop_zscore":  [3.0, 3.5, 4.0],
}

PERIODS = {
    "2023-2026 (без кризиса)": (date(2023, 1, 1), date(2026, 3, 18)),
    "2021-2026 (с кризисом)":  (date(2021, 1, 1), date(2026, 3, 18)),
}

TREND_TICKERS  = ["SBER", "GAZP", "LKOH"]
MR_TICKERS     = ["SBER", "GAZP", "LKOH"]
PAIRS_TICKERS  = ["SBER", "VTBR"]


# ---------------------------------------------------------------------------
# Построение DataFrame с индикаторами (универсальный, параметризованный)
# ---------------------------------------------------------------------------

def build_df(candles: list[OHLCVBar]) -> pl.DataFrame:
    return pl.DataFrame({
        "date":   [c.dt for c in candles],
        "open":   [c.open for c in candles],
        "high":   [c.high for c in candles],
        "low":    [c.low for c in candles],
        "close":  [c.close for c in candles],
        "volume": [c.volume for c in candles],
    }).sort("date")


def add_indicators_trend(df: pl.DataFrame, ema_fast: int, ema_slow: int) -> pl.DataFrame:
    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]

    ema_f  = calculate_ema(close, ema_fast)
    ema_s  = calculate_ema(close, ema_slow)
    ema200 = calculate_ema(close, 200)
    rsi14  = calculate_rsi(close, 14)
    macd_d = calculate_macd(close)
    adx_d  = calculate_adx(high, low, close, 14)
    atr14  = calculate_atr(high, low, close, 14)
    vol_r  = calculate_volume_ratio(volume, 20)

    return df.with_columns([
        ema_f.alias("ema_fast"),
        ema_s.alias("ema_slow"),
        ema200.alias("ema_200"),
        rsi14.alias("rsi_14"),
        macd_d["histogram"].alias("macd_hist"),
        adx_d["adx"].alias("adx"),
        adx_d["di_plus"].alias("di_plus"),
        adx_d["di_minus"].alias("di_minus"),
        atr14.alias("atr"),
        vol_r.alias("vol_ratio"),
    ])


def add_indicators_mr(df: pl.DataFrame, bb_period: int, bb_std: float) -> pl.DataFrame:
    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]

    ema200 = calculate_ema(close, 200)
    rsi2   = calculate_rsi(close, 2)
    rsi14  = calculate_rsi(close, 14)
    bb_d   = calculate_bollinger(close, bb_period, bb_std)
    atr14  = calculate_atr(high, low, close, 14)

    return df.with_columns([
        ema200.alias("ema_200"),
        rsi2.alias("rsi_2"),
        rsi14.alias("rsi_14"),
        bb_d["bb_upper"].alias("bb_upper"),
        bb_d["bb_lower"].alias("bb_lower"),
        atr14.alias("atr"),
    ])


# ---------------------------------------------------------------------------
# Метрики
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    return_pct: float
    sharpe: float
    max_dd: float
    win_rate: float
    n_trades: int


def calc_metrics(equity_curve: list[float], trades_pnl: list[float]) -> BacktestResult:
    if len(equity_curve) < 2:
        return BacktestResult(0.0, 0.0, 0.0, 0.0, 0)

    initial = equity_curve[0]
    final   = equity_curve[-1]
    ret_pct = (final / initial - 1) * 100

    # Sharpe по сделкам
    n = len(trades_pnl)
    if n >= 3:
        mean_r = statistics.mean(trades_pnl)
        std_r  = statistics.stdev(trades_pnl)
        sharpe = (mean_r / std_r * math.sqrt(max(n / 5, 1))) if std_r > 1e-8 else 0.0
    else:
        sharpe = 0.0

    # Max Drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    wins = sum(1 for p in trades_pnl if p > 0)
    wr = wins / n * 100 if n > 0 else 0.0

    return BacktestResult(
        return_pct=round(ret_pct, 2),
        sharpe=round(sharpe, 3),
        max_dd=round(max_dd * 100, 2),
        win_rate=round(wr, 1),
        n_trades=n,
    )


# ---------------------------------------------------------------------------
# Бэктест Trend Following (упрощённый, параметризованный)
# ---------------------------------------------------------------------------

def backtest_trend(
    dfs: dict[str, pl.DataFrame],
    rsi_buy: float,
    rsi_sell: float,
    adx_threshold: float,
    atr_stop_mult: float,
) -> BacktestResult:
    """Бэктест Trend Following по нескольким тикерам.

    Логика входа:
    - ADX > threshold (сильный тренд)
    - Цена выше EMA slow (направление тренда)
    - EMA fast > EMA slow (ускорение вверх)
    - MACD histogram > 0 (импульс)
    - rsi_buy: RSI14 < rsi_buy ИЛИ RSI14 показал пуллбек (упал с локального пика).
      rsi_buy=[30..45] интерпретируется как: RSI14 < (rsi_buy + 20),
      т.к. в тренде RSI редко падает ниже 45.
    - Выход: trailing stop, RSI > rsi_sell, цена ниже EMA slow
    """
    capital_per_ticker = INITIAL_CAPITAL / len(dfs)
    all_equity: list[float] = []
    all_pnl: list[float] = []

    for ticker, df in dfs.items():
        equity       = capital_per_ticker
        position     = None
        equity_curve = [equity]
        trades_pnl: list[float] = []
        rows         = df.to_dicts()
        rsi_history: list[float] = []  # для определения пуллбека

        for row in rows:
            close    = row.get("close") or 0.0
            high_p   = row.get("high") or close
            low_p    = row.get("low") or close
            atr      = row.get("atr") or 0.0
            rsi      = row.get("rsi_14")
            adx      = row.get("adx")
            ema_fast = row.get("ema_fast")
            ema_slow = row.get("ema_slow")
            macd_h   = row.get("macd_hist")
            vol_r    = row.get("vol_ratio")

            required = [rsi, adx, ema_fast, ema_slow, macd_h, atr]
            if any(v is None or (isinstance(v, float) and v != v) for v in required):
                equity_curve.append(equity)
                continue
            if atr <= 0 or close <= 0:
                equity_curve.append(equity)
                continue

            rsi_history.append(rsi)

            # EXIT
            if position is not None:
                exit_price = None
                if high_p > position["peak"]:
                    position["peak"] = high_p
                    new_trail = position["peak"] - atr * atr_stop_mult
                    position["trail"] = max(position["trail"], new_trail)

                if low_p <= position["trail"]:
                    exit_price = position["trail"]
                elif rsi is not None and rsi > rsi_sell:
                    exit_price = close
                elif close < ema_slow:
                    exit_price = close

                if exit_price is not None:
                    pnl = (exit_price - position["entry"]) * position["lots"]
                    pnl -= position["entry"] * position["lots"] * COMMISSION_RT
                    equity += pnl
                    trades_pnl.append(pnl)
                    position = None

            # ENTRY
            if position is None:
                trend_ok = (
                    adx > adx_threshold
                    and close > ema_slow
                    and ema_fast > ema_slow * 0.99
                    and macd_h > 0
                    and (vol_r or 0) > 0.7
                )
                # rsi_buy параметр [30..45] → пересчитываем в реальный RSI-порог +20
                # rsi_buy=30 → входим при RSI < 50
                # rsi_buy=45 → входим при RSI < 65 (любой пуллбек)
                rsi_threshold = rsi_buy + 20.0
                # Дополнительно: RSI упал с локального пика (пуллбек)
                pullback_ok = rsi is not None and rsi < rsi_threshold
                if not pullback_ok and len(rsi_history) >= 3:
                    # Пуллбек: RSI сейчас ниже чем 3 бара назад на rsi_buy пунктов
                    pullback_ok = rsi < rsi_history[-3] - (rsi_buy - 25)

                if trend_ok and pullback_ok and atr > 0:
                    risk_per_share = atr * atr_stop_mult
                    risk_budget    = equity * 0.01
                    lots = max(1, int(risk_budget / risk_per_share))
                    max_lots = int(equity * 0.15 / close)
                    lots = min(lots, max(max_lots, 1))
                    stop = close - atr * atr_stop_mult
                    position = {
                        "entry": close,
                        "lots":  lots,
                        "trail": stop,
                        "peak":  close,
                    }

            equity_curve.append(equity)

        # Закрыть открытую позицию
        if position is not None and rows:
            last_close = rows[-1]["close"]
            pnl = (last_close - position["entry"]) * position["lots"]
            pnl -= position["entry"] * position["lots"] * COMMISSION_RT
            equity += pnl
            trades_pnl.append(pnl)
            equity_curve[-1] = equity

        all_equity.append(equity)
        all_pnl.extend(trades_pnl)

    # Суммарная equity curve — просто скалярный результат
    total_equity = sum(all_equity)
    total_curve = [INITIAL_CAPITAL, total_equity]
    return calc_metrics(total_curve, all_pnl)


# ---------------------------------------------------------------------------
# Бэктест Mean Reversion (параметризованный)
# ---------------------------------------------------------------------------

def backtest_mr(
    dfs: dict[str, pl.DataFrame],
    rsi2_buy: float,
    rsi2_sell: float,
    time_stop: int,
    bb_period: int,
    bb_std: float,
) -> BacktestResult:
    capital_per_ticker = INITIAL_CAPITAL / len(dfs)
    all_equity: list[float] = []
    all_pnl: list[float] = []

    for ticker, df in dfs.items():
        equity       = capital_per_ticker
        position     = None
        equity_curve = [equity]
        trades_pnl: list[float] = []
        rows = df.to_dicts()

        for i, row in enumerate(rows):
            close    = row.get("close") or 0.0
            high_p   = row.get("high") or close
            low_p    = row.get("low") or close
            atr      = row.get("atr") or 0.0
            rsi2     = row.get("rsi_2")
            ema200   = row.get("ema_200")
            bb_lower = row.get("bb_lower")
            bb_upper = row.get("bb_upper")

            required = [rsi2, ema200, bb_lower, atr]
            if any(v is None or (isinstance(v, float) and v != v) for v in required):
                equity_curve.append(equity)
                continue
            if atr <= 0 or close <= 0:
                equity_curve.append(equity)
                continue

            # EXIT
            if position is not None:
                days_held = i - position["entry_idx"]
                exit_price = None

                if rsi2 is not None and rsi2 > 70:
                    exit_price = close
                elif days_held >= time_stop:
                    exit_price = close
                elif low_p <= position["stop"]:
                    exit_price = position["stop"]

                if exit_price is not None:
                    pnl = (exit_price - position["entry"]) * position["lots"]
                    pnl -= position["entry"] * position["lots"] * COMMISSION_RT
                    equity += pnl
                    trades_pnl.append(pnl)
                    position = None

            # ENTRY
            if position is None:
                buy_signal = (
                    rsi2 is not None
                    and rsi2 < rsi2_buy
                    and ema200 is not None
                    and close > ema200
                    and bb_lower is not None
                    and close < bb_lower
                    and atr > 0
                )
                if buy_signal:
                    risk_budget = equity * 0.01
                    risk_per_sh = atr * 2.0
                    lots = max(1, int(risk_budget / risk_per_sh))
                    max_lots = int(equity * 0.15 / close)
                    lots = min(lots, max(max_lots, 1))
                    position = {
                        "entry":     close,
                        "lots":      lots,
                        "stop":      close - atr * 2.0,
                        "entry_idx": i,
                    }

            equity_curve.append(equity)

        if position is not None and rows:
            last_close = rows[-1]["close"]
            pnl = (last_close - position["entry"]) * position["lots"]
            pnl -= position["entry"] * position["lots"] * COMMISSION_RT
            equity += pnl
            trades_pnl.append(pnl)
            equity_curve[-1] = equity

        all_equity.append(equity)
        all_pnl.extend(trades_pnl)

    total_equity = sum(all_equity)
    total_curve = [INITIAL_CAPITAL, total_equity]
    return calc_metrics(total_curve, all_pnl)


# ---------------------------------------------------------------------------
# Бэктест Pairs Trading (параметризованный)
# ---------------------------------------------------------------------------

def backtest_pairs(
    df_a: pl.DataFrame,
    df_b: pl.DataFrame,
    lookback: int,
    entry_zscore: float,
    exit_zscore: float,
    stop_zscore: float,
) -> BacktestResult:
    """Market-neutral pairs backtest SBER/VTBR."""
    rows_a = df_a.sort("date").to_dicts()
    rows_b = df_b.sort("date").to_dicts()

    # Выровнять по датам
    dates_a = {r["date"]: r for r in rows_a}
    dates_b = {r["date"]: r for r in rows_b}
    common_dates = sorted(set(dates_a) & set(dates_b))

    if len(common_dates) < lookback + 20:
        return BacktestResult(0.0, 0.0, 0.0, 0.0, 0)

    equity = INITIAL_CAPITAL
    equity_curve = [equity]
    trades_pnl: list[float] = []

    # Позиция: long A / short B или наоборот
    pos = None  # dict: direction (1=longA/shortB, -1=shortA/longB), price_a, price_b, lots

    prices_a = [dates_a[d]["close"] for d in common_dates]
    prices_b = [dates_b[d]["close"] for d in common_dates]

    for i in range(lookback, len(common_dates)):
        window_a = prices_a[i - lookback: i]
        window_b = prices_b[i - lookback: i]

        # Hedge ratio OLS
        x = np.array(window_b)
        y = np.array(window_a)
        x_mean, y_mean = np.mean(x), np.mean(y)
        cov_xy = np.mean((x - x_mean) * (y - y_mean))
        var_x  = np.mean((x - x_mean) ** 2)
        hedge  = cov_xy / var_x if var_x > 1e-10 else 1.0

        # Spread и Z-score
        spread = np.array(window_a) - hedge * np.array(window_b)
        mean_s = np.mean(spread)
        std_s  = np.std(spread, ddof=1)
        if std_s < 1e-10:
            equity_curve.append(equity)
            continue
        zscore = float((spread[-1] - mean_s) / std_s)

        close_a = prices_a[i]
        close_b = prices_b[i]

        # EXIT
        if pos is not None:
            exit_now = False
            if abs(zscore) < exit_zscore:
                exit_now = True
            elif abs(zscore) > stop_zscore:
                exit_now = True

            if exit_now:
                direction = pos["direction"]
                # Long A / Short B:
                pnl_a = direction * (close_a - pos["price_a"]) * pos["lots"]
                pnl_b = -direction * (close_b - pos["price_b"]) * pos["lots"]
                pnl   = pnl_a + pnl_b
                pnl  -= (pos["price_a"] + pos["price_b"]) * pos["lots"] * COMMISSION_RT
                equity += pnl
                trades_pnl.append(pnl)
                pos = None

        # ENTRY
        if pos is None:
            if zscore > entry_zscore:
                # Спред высокий: Short A / Long B  (direction = -1)
                lots = max(1, int(equity * 0.05 / close_a))
                pos = {"direction": -1, "price_a": close_a, "price_b": close_b, "lots": lots}
            elif zscore < -entry_zscore:
                # Спред низкий: Long A / Short B  (direction = +1)
                lots = max(1, int(equity * 0.05 / close_a))
                pos = {"direction": 1, "price_a": close_a, "price_b": close_b, "lots": lots}

        equity_curve.append(equity)

    # Закрыть открытую позицию
    if pos is not None and common_dates:
        last_a = prices_a[-1]
        last_b = prices_b[-1]
        direction = pos["direction"]
        pnl = direction * (last_a - pos["price_a"]) * pos["lots"]
        pnl += -direction * (last_b - pos["price_b"]) * pos["lots"]
        pnl -= (pos["price_a"] + pos["price_b"]) * pos["lots"] * COMMISSION_RT
        equity += pnl
        trades_pnl.append(pnl)

    return calc_metrics(equity_curve, trades_pnl)


# ---------------------------------------------------------------------------
# Random Search
# ---------------------------------------------------------------------------

def random_combinations(param_grid: dict, n: int, seed: int = RANDOM_SEED) -> list[dict]:
    rng = random.Random(seed)
    result = []
    for _ in range(n):
        combo = {k: rng.choice(v) for k, v in param_grid.items()}
        result.append(combo)
    return result


# ---------------------------------------------------------------------------
# Форматирование таблицы результатов
# ---------------------------------------------------------------------------

def print_table(header: list[str], rows: list[list[str]]) -> None:
    widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(header)]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    def fmt_row(cells):
        return "|" + "|".join(f" {c:<{w}} " for c, w in zip(cells, widths)) + "|"
    print(sep)
    print(fmt_row(header))
    print(sep)
    for row in rows:
        print(fmt_row(row))
    print(sep)


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

async def main() -> None:
    t_start = time.perf_counter()
    print("\n" + "=" * 70)
    print("   ОПТИМИЗАЦИЯ ПАРАМЕТРОВ ТОРГОВЫХ СТРАТЕГИЙ — MOEX")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Загрузка данных один раз для всех периодов
    # -------------------------------------------------------------------------
    print("\nЗагрузка исторических данных...")
    full_from = date(2021, 1, 1)
    full_to   = date(2026, 3, 18)

    all_tickers = set(TREND_TICKERS + MR_TICKERS + PAIRS_TICKERS)
    raw_candles: dict[str, list[OHLCVBar]] = {}
    for ticker in all_tickers:
        candles = await get_candles(DB_PATH, ticker, full_from, full_to)
        raw_candles[ticker] = candles
        print(f"  {ticker}: {len(candles)} баров")

    print(f"Данные загружены за {time.perf_counter() - t_start:.1f}с\n")

    # -------------------------------------------------------------------------
    # Оптимизация Trend Following
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("=== ОПТИМИЗАЦИЯ: Trend Following ===")
    print("=" * 70)

    trend_combos = random_combinations(TREND_PARAMS, N_COMBINATIONS)
    trend_best_all: dict[str, list[dict]] = {}

    for period_name, (p_from, p_to) in PERIODS.items():
        print(f"\nПериод: {period_name}")

        # Подготовить DataFrame-ы с базовыми индикаторами
        # (ema_fast/ema_slow зависят от параметров, поэтому пересчитываем внутри)
        period_results: list[dict] = []

        # Кешировать raw df по тикеру для этого периода
        raw_dfs: dict[str, pl.DataFrame] = {}
        for ticker in TREND_TICKERS:
            candles = [c for c in raw_candles[ticker] if p_from <= c.dt <= p_to]
            if len(candles) < 220:
                continue
            raw_dfs[ticker] = build_df(candles)

        if not raw_dfs:
            print("  Недостаточно данных для периода")
            continue

        for combo in trend_combos:
            # Построить DF с индикаторами под текущие параметры
            dfs_with_ind: dict[str, pl.DataFrame] = {}
            for ticker, raw_df in raw_dfs.items():
                try:
                    dfs_with_ind[ticker] = add_indicators_trend(
                        raw_df,
                        ema_fast=combo["ema_fast"],
                        ema_slow=combo["ema_slow"],
                    )
                except Exception:
                    pass

            if not dfs_with_ind:
                continue

            try:
                res = backtest_trend(
                    dfs_with_ind,
                    rsi_buy=combo["rsi_buy"],
                    rsi_sell=combo["rsi_sell"],
                    adx_threshold=combo["adx_threshold"],
                    atr_stop_mult=combo["atr_stop_mult"],
                )
            except Exception:
                continue

            period_results.append({"combo": combo, "result": res})

        # Сортировка: приоритет — Sharpe, потом Return
        period_results.sort(key=lambda x: (x["result"].sharpe, x["result"].return_pct), reverse=True)
        trend_best_all[period_name] = period_results[:3]

        top3_rows = []
        for rank, item in enumerate(period_results[:3], 1):
            c = item["combo"]
            r = item["result"]
            top3_rows.append([
                str(rank),
                str(c["rsi_buy"]),
                str(c["rsi_sell"]),
                str(c["adx_threshold"]),
                f"{c['atr_stop_mult']:.1f}",
                str(c["ema_fast"]),
                str(c["ema_slow"]),
                f"{r.return_pct:+.1f}%",
                f"{r.sharpe:.3f}",
                f"-{r.max_dd:.1f}%",
                f"{r.win_rate:.0f}%",
                str(r.n_trades),
            ])

        print_table(
            ["#", "RSI buy", "RSI sell", "ADX", "ATR mult", "EMA fast", "EMA slow",
             "Return", "Sharpe", "MaxDD", "Win%", "Trades"],
            top3_rows if top3_rows else [["—"] * 12],
        )

    # -------------------------------------------------------------------------
    # Оптимизация Mean Reversion
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("=== ОПТИМИЗАЦИЯ: Mean Reversion ===")
    print("=" * 70)

    mr_combos = random_combinations(MR_PARAMS, N_COMBINATIONS, seed=RANDOM_SEED + 1)
    mr_best_all: dict[str, list[dict]] = {}

    for period_name, (p_from, p_to) in PERIODS.items():
        print(f"\nПериод: {period_name}")

        period_results: list[dict] = []
        raw_dfs: dict[str, pl.DataFrame] = {}
        for ticker in MR_TICKERS:
            candles = [c for c in raw_candles[ticker] if p_from <= c.dt <= p_to]
            if len(candles) < 220:
                continue
            raw_dfs[ticker] = build_df(candles)

        if not raw_dfs:
            print("  Недостаточно данных для периода")
            continue

        for combo in mr_combos:
            dfs_with_ind: dict[str, pl.DataFrame] = {}
            for ticker, raw_df in raw_dfs.items():
                try:
                    dfs_with_ind[ticker] = add_indicators_mr(
                        raw_df,
                        bb_period=combo["bb_period"],
                        bb_std=combo["bb_std"],
                    )
                except Exception:
                    pass

            if not dfs_with_ind:
                continue

            try:
                res = backtest_mr(
                    dfs_with_ind,
                    rsi2_buy=combo["rsi2_buy"],
                    rsi2_sell=combo["rsi2_sell"],
                    time_stop=combo["time_stop"],
                    bb_period=combo["bb_period"],
                    bb_std=combo["bb_std"],
                )
            except Exception:
                continue

            period_results.append({"combo": combo, "result": res})

        period_results.sort(key=lambda x: (x["result"].sharpe, x["result"].return_pct), reverse=True)
        mr_best_all[period_name] = period_results[:3]

        top3_rows = []
        for rank, item in enumerate(period_results[:3], 1):
            c = item["combo"]
            r = item["result"]
            top3_rows.append([
                str(rank),
                str(c["rsi2_buy"]),
                str(c["rsi2_sell"]),
                str(c["time_stop"]),
                str(c["bb_period"]),
                f"{c['bb_std']:.1f}",
                f"{r.return_pct:+.1f}%",
                f"{r.sharpe:.3f}",
                f"-{r.max_dd:.1f}%",
                f"{r.win_rate:.0f}%",
                str(r.n_trades),
            ])

        print_table(
            ["#", "RSI2 buy", "RSI2 sell", "Time stop", "BB period", "BB std",
             "Return", "Sharpe", "MaxDD", "Win%", "Trades"],
            top3_rows if top3_rows else [["—"] * 11],
        )

    # -------------------------------------------------------------------------
    # Оптимизация Pairs Trading (SBER/VTBR)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("=== ОПТИМИЗАЦИЯ: Pairs Trading (SBER/VTBR) ===")
    print("=" * 70)

    pairs_combos = random_combinations(PAIRS_PARAMS, N_COMBINATIONS, seed=RANDOM_SEED + 2)
    pairs_best_all: dict[str, list[dict]] = {}

    for period_name, (p_from, p_to) in PERIODS.items():
        print(f"\nПериод: {period_name}")

        candles_a = [c for c in raw_candles["SBER"] if p_from <= c.dt <= p_to]
        candles_b = [c for c in raw_candles["VTBR"] if p_from <= c.dt <= p_to]

        if len(candles_a) < 150 or len(candles_b) < 150:
            print("  Недостаточно данных для периода")
            continue

        df_a = build_df(candles_a)
        df_b = build_df(candles_b)

        period_results: list[dict] = []

        for combo in pairs_combos:
            if combo["exit_zscore"] >= combo["entry_zscore"]:
                continue  # невалидная комбинация

            try:
                res = backtest_pairs(
                    df_a, df_b,
                    lookback=combo["lookback"],
                    entry_zscore=combo["entry_zscore"],
                    exit_zscore=combo["exit_zscore"],
                    stop_zscore=combo["stop_zscore"],
                )
            except Exception:
                continue

            period_results.append({"combo": combo, "result": res})

        period_results.sort(key=lambda x: (x["result"].sharpe, x["result"].return_pct), reverse=True)
        pairs_best_all[period_name] = period_results[:3]

        top3_rows = []
        for rank, item in enumerate(period_results[:3], 1):
            c = item["combo"]
            r = item["result"]
            top3_rows.append([
                str(rank),
                str(c["lookback"]),
                f"{c['entry_zscore']:.1f}",
                f"{c['exit_zscore']:.2f}",
                f"{c['stop_zscore']:.1f}",
                f"{r.return_pct:+.1f}%",
                f"{r.sharpe:.3f}",
                f"-{r.max_dd:.1f}%",
                f"{r.win_rate:.0f}%",
                str(r.n_trades),
            ])

        print_table(
            ["#", "Lookback", "Entry Z", "Exit Z", "Stop Z",
             "Return", "Sharpe", "MaxDD", "Win%", "Trades"],
            top3_rows if top3_rows else [["—"] * 10],
        )

    # -------------------------------------------------------------------------
    # Итоговые рекомендации
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("=== РЕКОМЕНДУЕМЫЕ ПАРАМЕТРЫ (лучшие по Sharpe, период без кризиса) ===")
    print("=" * 70)

    nc_key = "2023-2026 (без кризиса)"
    full_key = "2021-2026 (с кризисом)"

    def best_item(best_all: dict, period_key: str) -> Optional[dict]:
        items = best_all.get(period_key, [])
        return items[0] if items else None

    # Trend Following
    best_trend = best_item(trend_best_all, nc_key)
    if best_trend:
        c = best_trend["combo"]
        r = best_trend["result"]
        print(f"\nTrend Following:")
        print(f"  RSI buy={c['rsi_buy']}, RSI sell={c['rsi_sell']}, ADX>={c['adx_threshold']}")
        print(f"  ATR stop mult={c['atr_stop_mult']}, EMA fast={c['ema_fast']}, EMA slow={c['ema_slow']}")
        print(f"  Return={r.return_pct:+.1f}%, Sharpe={r.sharpe:.3f}, MaxDD=-{r.max_dd:.1f}%, Win={r.win_rate:.0f}%")

        best_trend_full = best_item(trend_best_all, full_key)
        if best_trend_full:
            r2 = best_trend_full["result"]
            print(f"  На полном периоде: Return={r2.return_pct:+.1f}%, Sharpe={r2.sharpe:.3f}")

    # Mean Reversion
    best_mr = best_item(mr_best_all, nc_key)
    if best_mr:
        c = best_mr["combo"]
        r = best_mr["result"]
        print(f"\nMean Reversion:")
        print(f"  RSI2 buy<{c['rsi2_buy']}, RSI2 sell>{c['rsi2_sell']}, Time stop={c['time_stop']}дн")
        print(f"  BB period={c['bb_period']}, BB std={c['bb_std']:.1f}")
        print(f"  Return={r.return_pct:+.1f}%, Sharpe={r.sharpe:.3f}, MaxDD=-{r.max_dd:.1f}%, Win={r.win_rate:.0f}%")

        best_mr_full = best_item(mr_best_all, full_key)
        if best_mr_full:
            r2 = best_mr_full["result"]
            print(f"  На полном периоде: Return={r2.return_pct:+.1f}%, Sharpe={r2.sharpe:.3f}")

    # Pairs Trading
    best_pairs = best_item(pairs_best_all, nc_key)
    if best_pairs:
        c = best_pairs["combo"]
        r = best_pairs["result"]
        print(f"\nPairs Trading (SBER/VTBR):")
        print(f"  Lookback={c['lookback']}, Entry Z={c['entry_zscore']:.1f}, Exit Z={c['exit_zscore']:.2f}, Stop Z={c['stop_zscore']:.1f}")
        print(f"  Return={r.return_pct:+.1f}%, Sharpe={r.sharpe:.3f}, MaxDD=-{r.max_dd:.1f}%, Win={r.win_rate:.0f}%")

        best_pairs_full = best_item(pairs_best_all, full_key)
        if best_pairs_full:
            r2 = best_pairs_full["result"]
            print(f"  На полном периоде: Return={r2.return_pct:+.1f}%, Sharpe={r2.sharpe:.3f}")

    elapsed = time.perf_counter() - t_start
    print(f"\n{'=' * 70}")
    print(f"Оптимизация завершена за {elapsed:.1f} секунд")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
