"""Быстрый просмотр статуса торговой системы.

Загружает данные из SQLite (signals + candles) и показывает текущее
состояние портфеля через TradingPipeline.

Запуск:
    python scripts/trading_status.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

sys.path.insert(0, str(_PROJECT_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

import aiosqlite  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.main import TradingPipeline, configure_logging  # noqa: E402


async def _last_cycle_time(db_path: str) -> str:
    """Вернуть дату последнего сигнала из таблицы signals."""
    sql = "SELECT MAX(created_at) FROM signals"
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute(sql) as cursor:
            row = await cursor.fetchone()
    if row and row[0]:
        return str(row[0])
    return "нет данных"


async def _weekly_stats(db_path: str) -> tuple[int, int]:
    """Вернуть (всего сигналов за неделю, buy-сигналов за неделю)."""
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    sql_total = "SELECT COUNT(*) FROM signals WHERE date >= ?"
    sql_buy = "SELECT COUNT(*) FROM signals WHERE date >= ? AND direction = 'long'"
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute(sql_total, (week_ago,)) as cur:
            total_row = await cur.fetchone()
        async with conn.execute(sql_buy, (week_ago,)) as cur:
            buy_row = await cur.fetchone()
    total = total_row[0] if total_row else 0
    buy = buy_row[0] if buy_row else 0
    return total, buy


async def main() -> None:
    configure_logging("WARNING")  # Подавляем лишний вывод structlog

    settings = get_settings()
    db_path = str(settings.db_path_resolved)

    # Поднимаем pipeline для получения реального состояния портфеля
    pipeline = TradingPipeline()
    portfolio = await pipeline._executor.get_portfolio()
    positions = await pipeline._executor.get_positions()
    trade_log = getattr(pipeline._executor, "trade_log", [])

    # Дневной P&L — из trade_log за сегодня
    today_str = date.today().isoformat()
    daily_pnl = sum(
        t.get("pnl", 0.0)
        for t in trade_log
        if str(t.get("date", "")).startswith(today_str)
    )

    # Данные из БД
    last_cycle = await _last_cycle_time(db_path)
    total_signals, buy_signals = await _weekly_stats(db_path)

    # Просадка от пика
    drawdown_pct = portfolio.drawdown * 100

    print()
    print("=== Статус торговой системы ===")
    print(f"Последний запуск: {last_cycle}")
    print(f"Режим:            {settings.trading_mode}")
    print(f"Портфель:         {portfolio.equity:>12,.0f} руб.")
    print(f"  Кэш:            {portfolio.cash:>12,.0f} руб.")
    print(f"Открытых позиций: {len(positions)}")

    if positions:
        for pos in positions:
            pnl_str = f"{pos.unrealized_pnl:+,.0f} руб."
            days_held = (datetime.utcnow() - pos.opened_at).days
            print(
                f"  {pos.ticker:<6} {pos.direction:<5} x{pos.lots}л"
                f" | вход {pos.entry_price:,.0f}"
                f" | тек. {pos.current_price:,.0f}"
                f" | {pnl_str}"
                f" | {days_held}д"
            )

    print(f"Дневной P&L:      {daily_pnl:>+12,.0f} руб.")
    print(f"Просадка от пика: {drawdown_pct:.1f}%")
    print(f"Сигналов за неделю: {total_signals} (buy: {buy_signals})")
    print()


if __name__ == "__main__":
    asyncio.run(main())
