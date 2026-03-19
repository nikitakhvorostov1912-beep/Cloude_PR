"""Бэктест стратегии Trend Following на Si (USD/RUB).

Стратегия:
- EMA(20)/EMA(50) crossover + ADX(14) > 25
- Position sizing: 10% от портфеля
- Комиссии: 0.01% per side (фьючерсы дешевле акций)
- Time stop: 20 дней

Метрики:
- Total Return, Sharpe Ratio, Max Drawdown, Win Rate
- Сравнение с buy & hold USD

Данные: USDRUB из SQLite (загружается через scripts/load_si_data.py)

Запуск: python -m scripts.backtest_si
"""
from __future__ import annotations

import asyncio
import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer(colors=True)],
)
log = structlog.get_logger()

from src.data.db import get_candles
from src.models.market import OHLCVBar
from src.strategy.futures_si import _adx, _atr, _ema

DB_PATH = "data/trading.db"
TICKER = "USDRUB"
INITIAL_CAPITAL = 1_000_000.0
FROM_DATE = date(2021, 1, 1)
TO_DATE = date.today()

# Параметры стратегии
EMA_FAST = 20
EMA_SLOW = 50
ADX_THRESHOLD = 25.0
ATR_PERIOD = 14
ATR_STOP_MULT = 2.0
ATR_TARGET_MULT = 3.0
COMMISSION_PER_SIDE = 0.0001   # 0.01% per side
POSITION_SIZE_PCT = 0.10       # 10% от портфеля
TIME_STOP_DAYS = 20


def backtest_si(
    bars: list[OHLCVBar],
    capital: float,
) -> dict:
    """Бэктест Si Trend Following стратегии.

    Args:
        bars: Список OHLCVBar для USDRUB.
        capital: Начальный капитал.

    Returns:
        Словарь с метриками бэктеста.
    """
    closes = [bar.close for bar in bars]
    n = len(bars)

    ema_fast_series = _ema(closes, EMA_FAST)
    ema_slow_series = _ema(closes, EMA_SLOW)
    atr_series = _atr(bars, ATR_PERIOD)
    adx_series = _adx(bars, ATR_PERIOD)

    equity = capital
    equity_curve: list[float] = [capital]
    trades: list[dict] = []

    # Позиция: None или dict
    position: dict | None = None

    # Минимальный индекс для начала торговли — когда все индикаторы готовы
    start_idx = ADX_THRESHOLD  # ADX требует период*2 баров
    # Найдём первый индекс где ADX не NaN
    first_valid = next(
        (i for i in range(n) if _is_valid(adx_series[i])),
        n,
    )

    for i in range(first_valid, n):
        ema_fast = ema_fast_series[i]
        ema_slow = ema_slow_series[i]
        atr = atr_series[i]
        adx = adx_series[i]

        if not all(_is_valid(v) for v in [ema_fast, ema_slow, atr, adx]):
            equity_curve.append(equity)
            continue

        price = closes[i]
        bar_date = bars[i].dt

        trend_up = ema_fast > ema_slow
        trend_down = ema_fast < ema_slow
        trend_confirmed = adx > ADX_THRESHOLD

        # ─── EXIT ────────────────────────────────────────────────────────────
        if position is not None:
            days_held = i - position["entry_idx"]
            direction = position["direction"]
            exit_reason: str | None = None
            exit_price = price

            if direction == "long":
                if price <= position["stop_loss"]:
                    exit_reason = "stop_loss"
                elif price >= position["take_profit"]:
                    exit_reason = "take_profit"
                elif not trend_up:
                    exit_reason = "trend_reversal"
                elif days_held >= TIME_STOP_DAYS:
                    exit_reason = "time_stop"
            else:  # short
                if price >= position["stop_loss"]:
                    exit_reason = "stop_loss"
                elif price <= position["take_profit"]:
                    exit_reason = "take_profit"
                elif not trend_down:
                    exit_reason = "trend_reversal"
                elif days_held >= TIME_STOP_DAYS:
                    exit_reason = "time_stop"

            if exit_reason is not None:
                entry_price = position["entry_price"]
                position_value = position["position_value"]
                units = position_value / entry_price

                if direction == "long":
                    gross_pnl = (exit_price - entry_price) * units
                else:
                    gross_pnl = (entry_price - exit_price) * units

                # Комиссии: entry + exit
                commission = position_value * COMMISSION_PER_SIDE * 2
                net_pnl = gross_pnl - commission

                equity += net_pnl
                equity_curve.append(equity)

                pnl_pct = net_pnl / position_value * 100

                trades.append({
                    "direction": direction,
                    "entry_date": position["entry_date"],
                    "exit_date": bar_date,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "days_held": days_held,
                    "gross_pnl": round(gross_pnl, 2),
                    "commission": round(commission, 2),
                    "net_pnl": round(net_pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "exit_reason": exit_reason,
                })

                position = None
                continue

        # ─── ENTRY ───────────────────────────────────────────────────────────
        if position is None and trend_confirmed:
            position_value = equity * POSITION_SIZE_PCT
            stop_distance = atr * ATR_STOP_MULT
            target_distance = atr * ATR_TARGET_MULT

            if trend_up:
                stop_loss = price - stop_distance
                take_profit = price + target_distance
                position = {
                    "direction": "long",
                    "entry_price": price,
                    "entry_date": bar_date,
                    "entry_idx": i,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "position_value": position_value,
                }
            elif trend_down:
                stop_loss = price + stop_distance
                take_profit = price - target_distance
                position = {
                    "direction": "short",
                    "entry_price": price,
                    "entry_date": bar_date,
                    "entry_idx": i,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "position_value": position_value,
                }

        equity_curve.append(equity)

    # Закрыть открытую позицию по последней цене
    if position is not None and n > 0:
        last_price = closes[-1]
        last_date = bars[-1].dt
        entry_price = position["entry_price"]
        position_value = position["position_value"]
        units = position_value / entry_price
        days_held = n - 1 - position["entry_idx"]

        if position["direction"] == "long":
            gross_pnl = (last_price - entry_price) * units
        else:
            gross_pnl = (entry_price - last_price) * units

        commission = position_value * COMMISSION_PER_SIDE * 2
        net_pnl = gross_pnl - commission
        equity += net_pnl

        trades.append({
            "direction": position["direction"],
            "entry_date": position["entry_date"],
            "exit_date": last_date,
            "entry_price": entry_price,
            "exit_price": last_price,
            "days_held": days_held,
            "gross_pnl": round(gross_pnl, 2),
            "commission": round(commission, 2),
            "net_pnl": round(net_pnl, 2),
            "pnl_pct": round(net_pnl / position_value * 100, 2),
            "exit_reason": "end_of_data",
        })

    # Метрики
    total_return_pct = (equity / capital - 1) * 100
    wins = [t for t in trades if t["net_pnl"] > 0]
    losses = [t for t in trades if t["net_pnl"] <= 0]
    win_rate = len(wins) / max(len(trades), 1) * 100

    sharpe = _calculate_sharpe(equity_curve)
    max_dd = _calculate_max_drawdown(equity_curve)

    total_pnl = sum(t["net_pnl"] for t in trades)
    avg_win = sum(t["net_pnl"] for t in wins) / max(len(wins), 1)
    avg_loss = sum(t["net_pnl"] for t in losses) / max(len(losses), 1)
    profit_factor = abs(avg_win / avg_loss) if losses and avg_loss != 0 else float("inf")

    avg_days_held = sum(t["days_held"] for t in trades) / max(len(trades), 1)

    return {
        "ticker": TICKER,
        "trades": trades,
        "num_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "final_equity": round(equity, 2),
        "return_pct": round(total_return_pct, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "avg_days_held": round(avg_days_held, 1),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else None,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "equity_curve": equity_curve,
    }


def buy_and_hold_usdrub(bars: list[OHLCVBar], capital: float) -> dict:
    """Расчёт Buy & Hold USD стратегии для сравнения.

    Покупаем USD на всю сумму в начале, продаём в конце.

    Args:
        bars: Список OHLCVBar для USDRUB.
        capital: Начальный капитал в RUB.

    Returns:
        Словарь с метриками buy & hold.
    """
    if len(bars) < 2:
        return {"return_pct": 0.0, "final_equity": capital}

    entry_price = bars[0].close
    exit_price = bars[-1].close

    # Количество USD
    usd_amount = capital / entry_price
    final_equity = usd_amount * exit_price

    # Комиссия один раз (вход + выход)
    commission = capital * COMMISSION_PER_SIDE * 2
    final_equity -= commission

    return_pct = (final_equity / capital - 1) * 100

    return {
        "strategy": "Buy & Hold USD",
        "entry_date": str(bars[0].dt),
        "exit_date": str(bars[-1].dt),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "initial_capital": capital,
        "final_equity": round(final_equity, 2),
        "return_pct": round(return_pct, 2),
    }


def _is_valid(v: float) -> bool:
    """Проверить что значение не NaN и не None."""
    if v is None:
        return False
    try:
        return not math.isnan(v)
    except (TypeError, ValueError):
        return False


def _calculate_sharpe(equity_curve: list[float], risk_free_daily: float = 0.0) -> float:
    """Annualized Sharpe Ratio на основе кривой капитала."""
    if len(equity_curve) < 2:
        return 0.0

    returns = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] > 0
    ]

    if not returns:
        return 0.0

    mean_ret = sum(returns) / len(returns)
    excess = [r - risk_free_daily for r in returns]
    mean_excess = sum(excess) / len(excess)

    if len(excess) < 2:
        return 0.0

    variance = sum((r - mean_excess) ** 2 for r in excess) / (len(excess) - 1)
    std_ret = math.sqrt(variance) if variance > 0 else 0.0

    if std_ret < 1e-10:
        return 0.0

    return (mean_ret / std_ret) * math.sqrt(252)


def _calculate_max_drawdown(equity_curve: list[float]) -> float:
    """Максимальная просадка как доля (0.0 — 1.0)."""
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return max_dd


async def main() -> None:
    """Запуск бэктеста Si Trend Following."""
    log.info(
        "backtest_si.start",
        ticker=TICKER,
        from_date=str(FROM_DATE),
        to_date=str(TO_DATE),
        capital=INITIAL_CAPITAL,
        ema_fast=EMA_FAST,
        ema_slow=EMA_SLOW,
        adx_threshold=ADX_THRESHOLD,
        position_size_pct=f"{POSITION_SIZE_PCT*100:.0f}%",
        commission=f"{COMMISSION_PER_SIDE*100:.3f}% per side",
    )

    # Загрузка данных
    bars = await get_candles(DB_PATH, TICKER, FROM_DATE, TO_DATE)

    if not bars:
        log.error(
            "no_data",
            ticker=TICKER,
            hint="Запустите сначала: python -m scripts.load_si_data",
        )
        return

    log.info("data_loaded", ticker=TICKER, bars=len(bars),
             first=str(bars[0].dt), last=str(bars[-1].dt),
             first_close=bars[0].close, last_close=bars[-1].close)

    # Бэктест стратегии
    result = backtest_si(bars, INITIAL_CAPITAL)

    # Buy & Hold для сравнения
    bah = buy_and_hold_usdrub(bars, INITIAL_CAPITAL)

    # ─── Вывод результатов ──────────────────────────────────────────────────
    log.info("=" * 70)
    log.info(
        "SI TREND FOLLOWING BACKTEST RESULTS",
        strategy=f"EMA({EMA_FAST})/EMA({EMA_SLOW}) + ADX > {ADX_THRESHOLD}",
        ticker=TICKER,
        period=f"{FROM_DATE} to {TO_DATE}",
        initial_capital=f"{INITIAL_CAPITAL:,.0f} RUB",
        final_equity=f"{result['final_equity']:,.0f} RUB",
        total_return=f"{result['return_pct']:+.2f}%",
        num_trades=result["num_trades"],
        win_rate=f"{result['wins']}/{result['num_trades']} ({result['win_rate']:.1f}%)",
        sharpe=f"{result['sharpe']:.3f}",
        max_drawdown=f"{result['max_drawdown_pct']:.2f}%",
        avg_days_held=f"{result['avg_days_held']:.1f}d",
        total_pnl=f"{result['total_pnl']:+,.0f} RUB",
        avg_win=f"{result['avg_win']:+,.0f} RUB",
        avg_loss=f"{result['avg_loss']:+,.0f} RUB",
        profit_factor=f"{result['profit_factor']:.2f}" if result["profit_factor"] else "∞",
    )

    log.info("-" * 70)
    log.info(
        "BUY & HOLD USD (сравнение)",
        entry=f"{bah['entry_price']:.2f}",
        exit=f"{bah['exit_price']:.2f}",
        final_equity=f"{bah['final_equity']:,.0f} RUB",
        total_return=f"{bah['return_pct']:+.2f}%",
    )

    # Оценка превосходства над buy & hold
    alpha = result["return_pct"] - bah["return_pct"]
    log.info(
        "alpha_vs_buy_hold",
        alpha=f"{alpha:+.2f}%",
        note="Положительная alpha = стратегия лучше пассивного держания USD",
    )

    # Лучшие и худшие сделки
    if result["trades"]:
        sorted_trades = sorted(result["trades"], key=lambda t: t["net_pnl"], reverse=True)

        log.info("TOP 5 BEST TRADES:")
        for t in sorted_trades[:5]:
            log.info(
                f"  {t['direction'].upper()} {t['entry_date']}→{t['exit_date']} "
                f"entry={t['entry_price']:.2f} exit={t['exit_price']:.2f} "
                f"PnL={t['net_pnl']:+,.0f} ({t['pnl_pct']:+.1f}%) "
                f"[{t['exit_reason']}]"
            )

        log.info("TOP 5 WORST TRADES:")
        for t in sorted_trades[-5:]:
            log.info(
                f"  {t['direction'].upper()} {t['entry_date']}→{t['exit_date']} "
                f"entry={t['entry_price']:.2f} exit={t['exit_price']:.2f} "
                f"PnL={t['net_pnl']:+,.0f} ({t['pnl_pct']:+.1f}%) "
                f"[{t['exit_reason']}]"
            )

        # Статистика по причинам выхода
        exit_reasons: dict[str, int] = {}
        for t in result["trades"]:
            exit_reasons[t["exit_reason"]] = exit_reasons.get(t["exit_reason"], 0) + 1

        log.info("EXIT REASONS:", **exit_reasons)

    # Вердикт
    log.info("=" * 70)
    sharpe = result["sharpe"]
    ret = result["return_pct"]

    if sharpe >= 1.0 and ret > 0:
        verdict = "PASS — Sharpe >= 1.0 и положительная доходность"
    elif sharpe >= 0.5 and ret > 0:
        verdict = "MARGINAL — Sharpe 0.5-1.0, требует оптимизации параметров"
    elif ret > bah["return_pct"]:
        verdict = "ALPHA — доходность выше buy&hold, но Sharpe < 0.5 (высокий риск)"
    else:
        verdict = "FAIL — доходность ниже buy&hold, стратегия неэффективна"

    log.info(f"VERDICT: {verdict}")


if __name__ == "__main__":
    asyncio.run(main())
