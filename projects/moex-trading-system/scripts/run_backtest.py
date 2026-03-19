"""Первый бэктест: простая стратегия RSI + EMA на данных MOEX.

Без Claude (экономим токены) — чисто алгоритмическая стратегия для валидации pipeline.

Стратегия:
- BUY: RSI(14) < 35 AND Close > EMA(200) AND ADX(14) > 20
- SELL: RSI(14) > 70 OR Close < EMA(50) OR Time > 30 дней
- Stop-Loss: 2.5 * ATR(14) от входа
- Position Size: 1.5% риска на сделку, max 15% на тикер

Запуск: python -m scripts.run_backtest
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import polars as pl

from src.data.db import get_candles
from src.models.market import OHLCVBar
from src.analysis.features import (
    calculate_rsi,
    calculate_ema,
    calculate_atr,
    calculate_adx,
    calculate_macd,
)

import structlog

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer(colors=True)],
)
log = structlog.get_logger()

DB_PATH = "data/trading.db"
TICKERS = ["SBER", "GAZP", "LKOH", "NVTK", "ROSN", "GMKN", "VTBR", "MGNT", "MTSS"]
INITIAL_CAPITAL = 1_000_000.0
RISK_PER_TRADE = 0.015  # 1.5%
MAX_POSITION_PCT = 0.15
ATR_MULT = 2.5
COMMISSION_RT = 0.002  # 0.2% round-trip


def build_dataframe(candles: list[OHLCVBar]) -> pl.DataFrame:
    """Конвертировать свечи в polars DataFrame."""
    return pl.DataFrame({
        "date": [c.dt for c in candles],
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
        "volume": [c.volume for c in candles],
    }).sort("date")


def add_indicators(df: pl.DataFrame) -> pl.DataFrame:
    """Добавить индикаторы к DataFrame."""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rsi = calculate_rsi(close, 14)
    ema50 = calculate_ema(close, 50)
    ema200 = calculate_ema(close, 200)
    atr = calculate_atr(high, low, close, 14)
    adx_data = calculate_adx(high, low, close, 14)
    macd_data = calculate_macd(close)

    return df.with_columns([
        rsi.alias("rsi_14"),
        ema50.alias("ema_50"),
        ema200.alias("ema_200"),
        atr.alias("atr_14"),
        adx_data["adx"].alias("adx_14"),
        macd_data["histogram"].alias("macd_hist"),
    ])


def backtest_ticker(
    ticker: str,
    df: pl.DataFrame,
    capital_per_ticker: float,
) -> dict:
    """Бэктест одного тикера."""
    trades: list[dict] = []
    position = None  # {"entry_price", "stop_loss", "lots", "entry_date", "entry_idx"}
    equity = capital_per_ticker

    rows = df.to_dicts()

    for i, row in enumerate(rows):
        close = row["close"]
        rsi = row.get("rsi_14")
        ema50 = row.get("ema_50")
        ema200 = row.get("ema_200")
        atr = row.get("atr_14")
        adx = row.get("adx_14")

        # Пропустить если индикаторы не рассчитаны (warmup)
        if any(v is None or v != v for v in [rsi, ema50, ema200, atr, adx]):  # NaN check
            continue
        if atr <= 0:
            continue

        dt = row["date"]

        # --- EXIT ---
        if position is not None:
            days_held = i - position["entry_idx"]
            hit_stop = close <= position["stop_loss"]
            hit_rsi_exit = rsi > 70
            hit_ema_exit = close < ema50 and adx > 25
            hit_time_exit = days_held > 30

            if hit_stop or hit_rsi_exit or hit_ema_exit or hit_time_exit:
                exit_price = position["stop_loss"] if hit_stop else close
                pnl = (exit_price - position["entry_price"]) * position["lots"]
                pnl -= position["entry_price"] * position["lots"] * COMMISSION_RT  # комиссии
                equity += pnl

                reason = "stop" if hit_stop else "rsi>70" if hit_rsi_exit else "ema_break" if hit_ema_exit else "time"
                trades.append({
                    "ticker": ticker,
                    "entry_date": position["entry_date"],
                    "exit_date": dt,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "lots": position["lots"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl / (position["entry_price"] * position["lots"]) * 100, 2),
                    "days_held": days_held,
                    "exit_reason": reason,
                })
                position = None

        # --- ENTRY ---
        if position is None:
            buy_signal = (
                rsi < 35
                and close > ema200
                and adx > 20
            )

            if buy_signal:
                stop_distance = atr * ATR_MULT
                risk_amount = equity * RISK_PER_TRADE
                lots = int(risk_amount / stop_distance)
                position_value = lots * close
                max_value = equity * MAX_POSITION_PCT

                if position_value > max_value:
                    lots = int(max_value / close)

                if lots > 0:
                    position = {
                        "entry_price": close,
                        "stop_loss": close - stop_distance,
                        "lots": lots,
                        "entry_date": dt,
                        "entry_idx": i,
                    }

    # Закрыть открытую позицию по последней цене
    if position is not None and rows:
        last = rows[-1]
        pnl = (last["close"] - position["entry_price"]) * position["lots"]
        equity += pnl
        trades.append({
            "ticker": ticker,
            "entry_date": position["entry_date"],
            "exit_date": last["date"],
            "entry_price": position["entry_price"],
            "exit_price": last["close"],
            "lots": position["lots"],
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / (position["entry_price"] * position["lots"]) * 100, 2),
            "days_held": len(rows) - position["entry_idx"],
            "exit_reason": "end_of_data",
        })

    return {
        "ticker": ticker,
        "trades": trades,
        "final_equity": round(equity, 2),
        "return_pct": round((equity / capital_per_ticker - 1) * 100, 2),
        "num_trades": len(trades),
        "wins": sum(1 for t in trades if t["pnl"] > 0),
        "losses": sum(1 for t in trades if t["pnl"] <= 0),
    }


async def main() -> None:
    """Запуск бэктеста по всем тикерам."""
    log.info("backtest_start", tickers=len(TICKERS), capital=INITIAL_CAPITAL)

    from_date = date(2021, 1, 1)
    to_date = date(2026, 3, 18)
    capital_per_ticker = INITIAL_CAPITAL / len(TICKERS)

    all_trades: list[dict] = []
    total_equity = 0.0
    results: list[dict] = []

    for ticker in TICKERS:
        candles = await get_candles(DB_PATH, ticker, from_date, to_date)
        if len(candles) < 250:
            log.warning("insufficient_data", ticker=ticker, bars=len(candles))
            total_equity += capital_per_ticker
            continue

        df = build_dataframe(candles)
        df = add_indicators(df)

        result = backtest_ticker(ticker, df, capital_per_ticker)
        results.append(result)
        all_trades.extend(result["trades"])
        total_equity += result["final_equity"]

        win_rate = result["wins"] / max(result["num_trades"], 1) * 100
        log.info("ticker_result",
                 ticker=ticker,
                 trades=result["num_trades"],
                 wins=result["wins"],
                 losses=result["losses"],
                 win_rate=f"{win_rate:.0f}%",
                 return_pct=f"{result['return_pct']:.1f}%",
                 final_equity=f"{result['final_equity']:,.0f}")

    # Итого
    total_return = (total_equity / INITIAL_CAPITAL - 1) * 100
    total_trades = len(all_trades)
    total_wins = sum(1 for t in all_trades if t["pnl"] > 0)
    total_pnl = sum(t["pnl"] for t in all_trades)
    avg_pnl = total_pnl / max(total_trades, 1)
    avg_win = sum(t["pnl"] for t in all_trades if t["pnl"] > 0) / max(total_wins, 1)
    avg_loss = sum(t["pnl"] for t in all_trades if t["pnl"] <= 0) / max(total_trades - total_wins, 1)

    log.info("=" * 60)
    log.info("BACKTEST RESULTS",
             strategy="RSI(14)<35 + EMA200 + ADX>20",
             period=f"{from_date} → {to_date}",
             initial_capital=f"{INITIAL_CAPITAL:,.0f}",
             final_equity=f"{total_equity:,.0f}",
             total_return=f"{total_return:.1f}%",
             total_trades=total_trades,
             win_rate=f"{total_wins}/{total_trades} ({total_wins/max(total_trades,1)*100:.0f}%)",
             avg_pnl=f"{avg_pnl:,.0f}",
             avg_win=f"{avg_win:,.0f}",
             avg_loss=f"{avg_loss:,.0f}",
             profit_factor=f"{abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "N/A")

    # Топ-5 лучших и худших сделок
    sorted_trades = sorted(all_trades, key=lambda t: t["pnl"], reverse=True)
    log.info("TOP 5 BEST TRADES:")
    for t in sorted_trades[:5]:
        log.info(f"  {t['ticker']} {t['entry_date']}→{t['exit_date']} PnL={t['pnl']:+,.0f} ({t['pnl_pct']:+.1f}%) [{t['exit_reason']}]")

    log.info("TOP 5 WORST TRADES:")
    for t in sorted_trades[-5:]:
        log.info(f"  {t['ticker']} {t['entry_date']}→{t['exit_date']} PnL={t['pnl']:+,.0f} ({t['pnl_pct']:+.1f}%) [{t['exit_reason']}]")


if __name__ == "__main__":
    asyncio.run(main())
