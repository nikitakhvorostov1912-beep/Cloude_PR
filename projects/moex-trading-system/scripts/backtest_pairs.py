"""Бэктест Pairs Trading стратегии.

Walk-forward бэктест на парах SBER/VTBR и LKOH/ROSN.
- Lookback: 60 дней
- Вход: |Z-score| > 2.0
- Выход: |Z-score| < 0.5
- Position sizing: равный капитал на обе ноги
- Комиссии: 0.1% RT для лонг, 0.15% RT для шорт (займ бумаг)
- Метрики: Return, Sharpe, MaxDD, Win Rate, кол-во сделок

Запуск: python -m scripts.backtest_pairs
"""

from __future__ import annotations

import asyncio
import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog

from src.data.db import get_candles
from src.models.market import OHLCVBar
from src.strategy.pairs_trading import (
    calculate_hedge_ratio,
    calculate_spread,
    calculate_zscore,
    check_cointegration,
)

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer(colors=True)],
)
log = structlog.get_logger()

DB_PATH = "data/trading.db"
INITIAL_CAPITAL = 1_000_000.0

PAIRS = [
    {"A": "SBER", "B": "VTBR", "sector": "banks"},
    {"A": "LKOH", "B": "ROSN", "sector": "oil"},
]

LOOKBACK = 60
ENTRY_ZSCORE = 2.0
EXIT_ZSCORE = 0.5
STOP_ZSCORE = 3.5
COMMISSION_LONG_RT = 0.001   # 0.1% round-trip для лонг
COMMISSION_SHORT_RT = 0.0015  # 0.15% round-trip для шорт (включает займ бумаг)


def align_series(
    bars_a: list[OHLCVBar],
    bars_b: list[OHLCVBar],
) -> tuple[list[OHLCVBar], list[OHLCVBar]]:
    """Выровнять два ряда свечей по общим датам.

    Args:
        bars_a: Свечи тикера A.
        bars_b: Свечи тикера B.

    Returns:
        Кортеж (aligned_a, aligned_b) — только даты присутствующие в обоих рядах.
    """
    dates_a = {bar.dt: bar for bar in bars_a}
    dates_b = {bar.dt: bar for bar in bars_b}
    common_dates = sorted(dates_a.keys() & dates_b.keys())

    aligned_a = [dates_a[d] for d in common_dates]
    aligned_b = [dates_b[d] for d in common_dates]
    return aligned_a, aligned_b


def backtest_pair(
    ticker_a: str,
    ticker_b: str,
    bars_a: list[OHLCVBar],
    bars_b: list[OHLCVBar],
    capital: float,
) -> dict:
    """Бэктест одной пары.

    Args:
        ticker_a: Тикер актива A.
        ticker_b: Тикер актива B.
        bars_a: Свечи актива A (уже выровнены по датам).
        bars_b: Свечи актива B (уже выровнены по датам).
        capital: Начальный капитал для пары.

    Returns:
        Словарь с метриками бэктеста.
    """
    trades: list[dict] = []
    equity_curve: list[float] = [capital]
    equity = capital

    # Позиция: None или dict с параметрами сделки
    position: dict | None = None

    n = len(bars_a)
    prices_a = [bar.close for bar in bars_a]
    prices_b = [bar.close for bar in bars_b]

    for i in range(LOOKBACK + 10, n):
        # Скользящее окно для расчёта
        window_start = max(0, i - LOOKBACK * 2)
        pa_window = prices_a[window_start:i]
        pb_window = prices_b[window_start:i]

        # Расчёт z-score
        hedge_ratio = calculate_hedge_ratio(pa_window, pb_window)
        spread = calculate_spread(pa_window, pb_window, hedge_ratio)
        zscore = calculate_zscore(spread, lookback=LOOKBACK)

        current_price_a = prices_a[i]
        current_price_b = prices_b[i]
        dt = bars_a[i].dt

        # --- EXIT ---
        if position is not None:
            days_held = i - position["entry_idx"]
            exit_reason = None

            if abs(zscore) < EXIT_ZSCORE:
                exit_reason = "mean_reversion"
            elif abs(zscore) > STOP_ZSCORE:
                exit_reason = "stop_loss"
            elif days_held > 30:
                exit_reason = "time_stop"

            if exit_reason is not None:
                # Расчёт P&L пары
                # Лонг нога
                long_ticker = position["long_ticker"]
                short_ticker = position["short_ticker"]
                long_entry = position["long_entry_price"]
                short_entry = position["short_entry_price"]
                lot_value = position["lot_value"]  # капитал на одну ногу

                if long_ticker == ticker_a:
                    long_exit_price = current_price_a
                    short_exit_price = current_price_b
                else:
                    long_exit_price = current_price_b
                    short_exit_price = current_price_a

                # Количество акций (по стоимости)
                long_shares = lot_value / long_entry
                short_shares = lot_value / short_entry

                # P&L
                long_pnl = (long_exit_price - long_entry) * long_shares
                short_pnl = (short_entry - short_exit_price) * short_shares

                # Комиссии
                long_commission = long_entry * long_shares * COMMISSION_LONG_RT
                short_commission = short_entry * short_shares * COMMISSION_SHORT_RT

                total_pnl = long_pnl + short_pnl - long_commission - short_commission
                equity += total_pnl
                equity_curve.append(equity)

                pnl_pct = total_pnl / (lot_value * 2) * 100

                trades.append({
                    "pair": f"{ticker_a}/{ticker_b}",
                    "long_ticker": long_ticker,
                    "short_ticker": short_ticker,
                    "entry_date": position["entry_date"],
                    "exit_date": dt,
                    "entry_zscore": round(position["entry_zscore"], 3),
                    "exit_zscore": round(zscore, 3),
                    "long_entry": long_entry,
                    "long_exit": long_exit_price,
                    "short_entry": short_entry,
                    "short_exit": short_exit_price,
                    "pnl": round(total_pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "days_held": days_held,
                    "exit_reason": exit_reason,
                })

                position = None
                continue

        # --- ENTRY ---
        if position is None:
            # Проверяем коинтеграцию на lookback-окне
            coint_window_a = prices_a[max(0, i - LOOKBACK):i]
            coint_window_b = prices_b[max(0, i - LOOKBACK):i]
            is_cointegrated, _ = check_cointegration(coint_window_a, coint_window_b)

            if not is_cointegrated:
                equity_curve.append(equity)
                continue

            # Равный капитал на каждую ногу
            lot_value = equity * 0.25  # 25% капитала на ногу = 50% суммарно

            if zscore > ENTRY_ZSCORE:
                # SHORT A + LONG B
                position = {
                    "long_ticker": ticker_b,
                    "short_ticker": ticker_a,
                    "long_entry_price": current_price_b,
                    "short_entry_price": current_price_a,
                    "lot_value": lot_value,
                    "entry_date": dt,
                    "entry_idx": i,
                    "entry_zscore": zscore,
                }
            elif zscore < -ENTRY_ZSCORE:
                # LONG A + SHORT B
                position = {
                    "long_ticker": ticker_a,
                    "short_ticker": ticker_b,
                    "long_entry_price": current_price_a,
                    "short_entry_price": current_price_b,
                    "lot_value": lot_value,
                    "entry_date": dt,
                    "entry_idx": i,
                    "entry_zscore": zscore,
                }

        equity_curve.append(equity)

    # Закрыть открытую позицию по последней цене
    if position is not None and n > 0:
        last_a = prices_a[-1]
        last_b = prices_b[-1]
        last_dt = bars_a[-1].dt

        long_ticker = position["long_ticker"]
        long_entry = position["long_entry_price"]
        short_entry = position["short_entry_price"]
        lot_value = position["lot_value"]
        days_held = n - 1 - position["entry_idx"]

        if long_ticker == ticker_a:
            long_exit_price = last_a
            short_exit_price = last_b
        else:
            long_exit_price = last_b
            short_exit_price = last_a

        long_shares = lot_value / long_entry
        short_shares = lot_value / short_entry

        long_pnl = (long_exit_price - long_entry) * long_shares
        short_pnl = (short_entry - short_exit_price) * short_shares
        long_commission = long_entry * long_shares * COMMISSION_LONG_RT
        short_commission = short_entry * short_shares * COMMISSION_SHORT_RT

        total_pnl = long_pnl + short_pnl - long_commission - short_commission
        equity += total_pnl
        pnl_pct = total_pnl / (lot_value * 2) * 100

        trades.append({
            "pair": f"{ticker_a}/{ticker_b}",
            "long_ticker": long_ticker,
            "short_ticker": position["short_ticker"],
            "entry_date": position["entry_date"],
            "exit_date": last_dt,
            "entry_zscore": round(position["entry_zscore"], 3),
            "exit_zscore": 0.0,
            "pnl": round(total_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "days_held": days_held,
            "exit_reason": "end_of_data",
        })

    # Метрики
    return_pct = (equity / capital - 1) * 100
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = len(wins) / max(len(trades), 1) * 100

    # Sharpe Ratio (упрощённый, на дневных доходностях)
    sharpe = _calculate_sharpe(equity_curve)

    # Max Drawdown
    max_dd = _calculate_max_drawdown(equity_curve)

    return {
        "pair": f"{ticker_a}/{ticker_b}",
        "trades": trades,
        "num_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(sum(t["pnl"] for t in trades), 2),
        "final_equity": round(equity, 2),
        "return_pct": round(return_pct, 2),
        "sharpe": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "avg_days_held": round(
            sum(t["days_held"] for t in trades) / max(len(trades), 1), 1
        ),
    }


def _calculate_sharpe(equity_curve: list[float], risk_free_daily: float = 0.0) -> float:
    """Рассчитать Sharpe Ratio на основе кривой капитала.

    Args:
        equity_curve: Список значений капитала.
        risk_free_daily: Безрисковая дневная ставка (по умолчанию 0).

    Returns:
        Annualized Sharpe Ratio.
    """
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

    sharpe = (mean_ret / std_ret) * math.sqrt(252)
    return sharpe


def _calculate_max_drawdown(equity_curve: list[float]) -> float:
    """Рассчитать максимальную просадку.

    Args:
        equity_curve: Список значений капитала.

    Returns:
        Максимальная просадка как доля (0.0 - 1.0).
    """
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
    """Запуск бэктеста pairs trading."""
    log.info("backtest_pairs.start",
             pairs=len(PAIRS),
             lookback=LOOKBACK,
             entry_zscore=ENTRY_ZSCORE,
             exit_zscore=EXIT_ZSCORE,
             capital=INITIAL_CAPITAL)

    from_date = date(2021, 1, 1)
    to_date = date(2026, 3, 18)
    capital_per_pair = INITIAL_CAPITAL / len(PAIRS)

    all_trades: list[dict] = []
    all_results: list[dict] = []
    total_equity = 0.0

    for pair in PAIRS:
        ticker_a = pair["A"]
        ticker_b = pair["B"]

        log.info("pair.loading", pair=f"{ticker_a}/{ticker_b}")
        bars_a = await get_candles(DB_PATH, ticker_a, from_date, to_date)
        bars_b = await get_candles(DB_PATH, ticker_b, from_date, to_date)

        log.info("pair.data_loaded",
                 pair=f"{ticker_a}/{ticker_b}",
                 bars_a=len(bars_a),
                 bars_b=len(bars_b))

        if len(bars_a) < LOOKBACK + 10 or len(bars_b) < LOOKBACK + 10:
            log.warning("pair.insufficient_data",
                        pair=f"{ticker_a}/{ticker_b}",
                        required=LOOKBACK + 10)
            total_equity += capital_per_pair
            continue

        # Выравниваем по общим датам
        bars_a, bars_b = align_series(bars_a, bars_b)

        log.info("pair.aligned", pair=f"{ticker_a}/{ticker_b}", common_bars=len(bars_a))

        result = backtest_pair(ticker_a, ticker_b, bars_a, bars_b, capital_per_pair)
        all_results.append(result)
        all_trades.extend(result["trades"])
        total_equity += result["final_equity"]

        log.info(
            "pair.result",
            pair=result["pair"],
            trades=result["num_trades"],
            wins=result["wins"],
            losses=result["losses"],
            win_rate=f"{result['win_rate']:.1f}%",
            total_pnl=f"{result['total_pnl']:+,.0f}",
            return_pct=f"{result['return_pct']:+.2f}%",
            sharpe=f"{result['sharpe']:.3f}",
            max_dd=f"{result['max_drawdown_pct']:.2f}%",
            avg_days_held=f"{result['avg_days_held']:.1f}",
        )

    # Итоговые метрики
    total_return_pct = (total_equity / INITIAL_CAPITAL - 1) * 100
    total_trades = len(all_trades)
    total_wins = sum(1 for t in all_trades if t["pnl"] > 0)
    total_pnl = sum(t["pnl"] for t in all_trades)
    avg_pnl = total_pnl / max(total_trades, 1)
    avg_win = sum(t["pnl"] for t in all_trades if t["pnl"] > 0) / max(total_wins, 1)
    avg_loss_count = total_trades - total_wins
    avg_loss = sum(t["pnl"] for t in all_trades if t["pnl"] <= 0) / max(avg_loss_count, 1)
    profit_factor = abs(avg_win / avg_loss) if avg_loss_count > 0 and avg_loss != 0 else float("inf")

    # Средний Sharpe по парам
    avg_sharpe = (
        sum(r["sharpe"] for r in all_results) / len(all_results)
        if all_results else 0.0
    )
    avg_max_dd = (
        sum(r["max_drawdown_pct"] for r in all_results) / len(all_results)
        if all_results else 0.0
    )

    log.info("=" * 70)
    log.info(
        "PAIRS TRADING BACKTEST RESULTS",
        strategy="Pairs Trading (Market-Neutral)",
        period=f"{from_date} to {to_date}",
        pairs=len(PAIRS),
        initial_capital=f"{INITIAL_CAPITAL:,.0f}",
        final_equity=f"{total_equity:,.0f}",
        total_return=f"{total_return_pct:+.2f}%",
        total_trades=total_trades,
        win_rate=f"{total_wins}/{total_trades} ({total_wins/max(total_trades,1)*100:.0f}%)",
        avg_pnl=f"{avg_pnl:+,.0f}",
        avg_win=f"{avg_win:+,.0f}",
        avg_loss=f"{avg_loss:+,.0f}",
        profit_factor=f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞",
        avg_sharpe=f"{avg_sharpe:.3f}",
        avg_max_drawdown=f"{avg_max_dd:.2f}%",
    )

    if all_trades:
        sorted_trades = sorted(all_trades, key=lambda t: t["pnl"], reverse=True)
        log.info("TOP 5 BEST TRADES:")
        for t in sorted_trades[:5]:
            log.info(
                f"  {t['pair']} LONG={t['long_ticker']} SHORT={t['short_ticker']} "
                f"{t['entry_date']}→{t['exit_date']} "
                f"PnL={t['pnl']:+,.0f} ({t['pnl_pct']:+.1f}%) "
                f"[{t['exit_reason']}]"
            )

        log.info("TOP 5 WORST TRADES:")
        for t in sorted_trades[-5:]:
            log.info(
                f"  {t['pair']} LONG={t['long_ticker']} SHORT={t['short_ticker']} "
                f"{t['entry_date']}→{t['exit_date']} "
                f"PnL={t['pnl']:+,.0f} ({t['pnl_pct']:+.1f}%) "
                f"[{t['exit_reason']}]"
            )

    # Детальные результаты по парам
    log.info("")
    log.info("RESULTS BY PAIR:")
    for r in all_results:
        log.info(
            f"  {r['pair']}: trades={r['num_trades']}, "
            f"win_rate={r['win_rate']:.1f}%, "
            f"return={r['return_pct']:+.2f}%, "
            f"sharpe={r['sharpe']:.3f}, "
            f"max_dd={r['max_drawdown_pct']:.2f}%, "
            f"avg_hold={r['avg_days_held']:.1f}d"
        )

    # Мнение о стратегии
    log.info("")
    if avg_sharpe >= 1.0 and total_return_pct > 8:
        log.info("VERDICT: PASS — Sharpe >= 1.0 и Return >= 8%")
    elif avg_sharpe >= 0.5:
        log.info("VERDICT: MARGINAL — Sharpe 0.5-1.0, стратегия требует оптимизации")
    else:
        log.info("VERDICT: FAIL — Sharpe < 0.5, стратегия убыточна на данном периоде")


if __name__ == "__main__":
    asyncio.run(main())
