"""Бэктест стратегии дивидендного гэпа.

Для каждой даты отсечки из DIVIDEND_HISTORY:
1. Находит цену закрытия ДО отсечки (T-1).
2. Находит цену открытия ПОСЛЕ отсечки (T+1) — это entry.
3. Торгует: BUY при открытии T+1, EXIT через min(20 дней, gap closure).
4. Stop-loss: entry - 5%.

Запуск: python -m scripts.backtest_dividend_gap
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog

from src.data.db import get_candles
from src.models.market import OHLCVBar
from src.strategy.dividend_gap import (
    DIVIDEND_HISTORY,
    _STOP_LOSS_PCT,
    _DEFAULT_TIME_STOP_DAYS,
    check_gap_closure,
)

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer(colors=True)],
)
log = structlog.get_logger()

DB_PATH = "data/trading.db"
COMMISSION_RT = 0.002  # 0.2% round-trip


def find_bar_on_or_after(candles: list[OHLCVBar], target_date: date) -> OHLCVBar | None:
    """Найти первый бар начиная с target_date (включительно)."""
    for bar in candles:
        if bar.dt >= target_date:
            return bar
    return None


def find_bar_before(candles: list[OHLCVBar], target_date: date) -> OHLCVBar | None:
    """Найти последний бар строго ДО target_date."""
    result: OHLCVBar | None = None
    for bar in candles:
        if bar.dt < target_date:
            result = bar
        else:
            break
    return result


def backtest_trade(
    candles: list[OHLCVBar],
    record_date: date,
    dividend_amount: float,
    max_days: int = _DEFAULT_TIME_STOP_DAYS,
) -> dict | None:
    """Симулировать одну сделку дивидендного гэпа.

    Args:
        candles: Все свечи тикера, отсортированные по дате ASC.
        record_date: Дата отсечки (T).
        dividend_amount: Сумма дивиденда в рублях.
        max_days: Максимальный временной стоп.

    Returns:
        Словарь с результатами сделки или None если данных недостаточно.
    """
    # T-1: закрытие до гэпа
    pre_gap_bar = find_bar_before(candles, record_date)
    if pre_gap_bar is None:
        return None

    # T+1: первый торговый день после отсечки
    from datetime import timedelta
    gap_day_start = record_date + timedelta(days=1)
    entry_bar = find_bar_on_or_after(candles, gap_day_start)
    if entry_bar is None:
        return None

    pre_gap_price = pre_gap_bar.close
    entry_price = entry_bar.open if entry_bar.open > 0 else entry_bar.close

    # Проверяем что гэп действительно произошёл
    actual_drop = pre_gap_price - entry_price
    gap_pct = actual_drop / pre_gap_price * 100

    if actual_drop < dividend_amount * 0.5:
        # Гэп не подтверждён (возможно данных нет или гэп не состоялся)
        return None

    # Симулируем удержание позиции
    entry_idx = candles.index(entry_bar)
    exit_price = entry_price
    exit_date = entry_bar.dt
    exit_reason = "end_of_data"
    days_held = 0

    for i in range(entry_idx + 1, len(candles)):
        bar = candles[i]
        days_held = i - entry_idx
        current_price = bar.close

        reason = check_gap_closure(
            entry_price=entry_price,
            pre_gap_price=pre_gap_price,
            current_price=current_price,
            days_held=days_held,
            max_days=max_days,
        )

        if reason is not None:
            if reason == "stop_loss":
                # Выход по стоп-лоссу — исполняется на открытии следующего дня
                exit_price = entry_price * (1.0 - _STOP_LOSS_PCT)
            else:
                exit_price = current_price
            exit_date = bar.dt
            exit_reason = reason
            break

    pnl_pct = (exit_price - entry_price) / entry_price * 100 - COMMISSION_RT * 100
    result_label = "Закрыт" if exit_reason == "gap_closed" else (
        "Стоп" if exit_reason == "stop_loss" else (
            "Тайм-стоп" if exit_reason == "time_stop" else "Нет данных"
        )
    )

    return {
        "record_date": record_date.isoformat(),
        "dividend_amount": dividend_amount,
        "gap_pct": round(gap_pct, 1),
        "pre_gap_price": round(pre_gap_price, 2),
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "exit_date": exit_date.isoformat(),
        "days_held": days_held,
        "exit_reason": exit_reason,
        "pnl_pct": round(pnl_pct, 2),
        "result_label": result_label,
    }


async def run_buy_hold(candles: list[OHLCVBar]) -> float:
    """Рассчитать доходность buy & hold за весь период данных."""
    if len(candles) < 2:
        return 0.0
    start = candles[0].close
    end = candles[-1].close
    return round((end - start) / start * 100, 1)


async def main() -> None:
    """Запуск бэктеста дивидендного гэпа по всем тикерам."""
    log.info("backtest_dividend_gap.start")

    # Загружаем данные за весь доступный период
    from_date = date(2022, 1, 1)
    to_date = date(2026, 3, 18)

    all_trades: list[dict] = []
    ticker_results: dict[str, list[dict]] = {}

    for ticker in sorted(DIVIDEND_HISTORY.keys()):
        candles = await get_candles(DB_PATH, ticker, from_date, to_date)
        if len(candles) < 10:
            log.warning("insufficient_data", ticker=ticker, bars=len(candles))
            continue

        buy_hold_return = await run_buy_hold(candles)
        trades: list[dict] = []

        for record_date_str, dividend_amount in DIVIDEND_HISTORY[ticker]:
            record_date = date.fromisoformat(record_date_str)
            if record_date < from_date or record_date > to_date:
                continue

            trade = backtest_trade(candles, record_date, dividend_amount)
            if trade is not None:
                trade["ticker"] = ticker
                trades.append(trade)
                all_trades.append(trade)

        ticker_results[ticker] = trades

        # Статистика по тикеру
        wins = [t for t in trades if t["pnl_pct"] > 0]
        losses = [t for t in trades if t["pnl_pct"] <= 0]
        avg_pnl = sum(t["pnl_pct"] for t in trades) / len(trades) if trades else 0.0
        win_rate = len(wins) / len(trades) * 100 if trades else 0.0

        log.info(
            "ticker_result",
            ticker=ticker,
            trades=len(trades),
            wins=len(wins),
            losses=len(losses),
            win_rate=f"{win_rate:.0f}%",
            avg_pnl=f"{avg_pnl:+.1f}%",
            buy_hold=f"{buy_hold_return:+.1f}%",
        )

    # ─── Печать таблицы результатов ──────────────────────────────────────────
    print()
    print("=" * 85)
    print("=== БЭКТЕСТ: Дивидендный гэп ===")
    print("=" * 85)
    header = (
        f"{'Тикер':<6} | {'Отсечка':<12} | {'Дивиденд':>9} | "
        f"{'Гэп,%':>6} | {'Дн.':>4} | {'PnL,%':>7} | Результат"
    )
    print(header)
    print("-" * 85)

    for ticker in sorted(ticker_results.keys()):
        for t in ticker_results[ticker]:
            row = (
                f"{ticker:<6} | {t['record_date']:<12} | "
                f"{t['dividend_amount']:>9.2f} | "
                f"{-t['gap_pct']:>+5.1f}% | "
                f"{t['days_held']:>4} | "
                f"{t['pnl_pct']:>+6.1f}% | "
                f"{t['result_label']}"
            )
            print(row)

    print("=" * 85)

    # ─── Итоговая статистика ──────────────────────────────────────────────────
    if not all_trades:
        print("Нет сделок для анализа.")
        return

    total_trades = len(all_trades)
    wins = [t for t in all_trades if t["pnl_pct"] > 0]
    losses = [t for t in all_trades if t["pnl_pct"] <= 0]
    win_rate = len(wins) / total_trades * 100
    avg_pnl = sum(t["pnl_pct"] for t in all_trades) / total_trades
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0.0
    avg_days = sum(t["days_held"] for t in all_trades) / total_trades

    gap_closed = sum(1 for t in all_trades if t["exit_reason"] == "gap_closed")
    time_stops = sum(1 for t in all_trades if t["exit_reason"] == "time_stop")
    stop_losses = sum(1 for t in all_trades if t["exit_reason"] == "stop_loss")

    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

    print(f"\nИтого: {total_trades} сделок")
    print(f"Win Rate: {len(wins)}/{total_trades} ({win_rate:.0f}%)")
    print(f"Средний PnL: {avg_pnl:+.1f}%")
    print(f"Средний выигрыш: {avg_win:+.1f}%  |  Средний убыток: {avg_loss:+.1f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Среднее время в позиции: {avg_days:.1f} дн.")
    print(f"Закрыт гэп: {gap_closed} | Тайм-стоп: {time_stops} | Стоп-лосс: {stop_losses}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
