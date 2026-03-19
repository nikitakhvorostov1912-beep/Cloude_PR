"""Аварийное закрытие ВСЕХ открытых позиций.

ВНИМАНИЕ: Этот скрипт закрывает все позиции рыночными ордерами
без дополнительных проверок риск-менеджмента.

Запуск:
    python scripts/emergency_close.py

Порядок работы:
    1. Показывает список открытых позиций
    2. Запрашивает подтверждение ("yes" для продолжения)
    3. Закрывает каждую позицию market-ордером
    4. Отправляет уведомление в Telegram
    5. Выводит итоговый отчёт
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

sys.path.insert(0, str(_PROJECT_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from src.main import TradingPipeline, configure_logging  # noqa: E402
from src.models.order import Order, OrderType  # noqa: E402


async def main() -> None:
    configure_logging("WARNING")

    pipeline = TradingPipeline()
    positions = await pipeline._executor.get_positions()

    print()
    print("=" * 60)
    print("  АВАРИЙНОЕ ЗАКРЫТИЕ ПОЗИЦИЙ")
    print("=" * 60)

    if not positions:
        print("Открытых позиций нет. Нечего закрывать.")
        print()
        return

    print(f"Найдено позиций: {len(positions)}")
    print()
    for pos in positions:
        pnl_str = f"{pos.unrealized_pnl:+,.0f} руб."
        print(
            f"  {pos.ticker:<6} {pos.direction:<5} x{pos.lots}л"
            f" | вход {pos.entry_price:,.0f}"
            f" | тек. {pos.current_price:,.0f}"
            f" | {pnl_str}"
        )

    print()
    print("ВНИМАНИЕ: Это закроет ВСЕ позиции рыночными ордерами!")
    answer = input("Вы уверены? (yes/no): ").strip().lower()

    if answer != "yes":
        print("Отменено.")
        return

    print()
    print("Закрываем позиции...")

    closed: list[dict] = []
    failed: list[str] = []

    for pos in positions:
        ticker = pos.ticker
        try:
            # Обновляем цену в executor перед ордером
            set_price = getattr(pipeline._executor, "set_market_price", None)
            if set_price is not None:
                set_price(ticker, float(pos.current_price))

            close_order = Order(
                order_id=str(uuid.uuid4()),
                ticker=ticker,
                direction=pos.direction,
                action="sell",
                order_type=OrderType.MARKET,
                lots=pos.lots,
                lot_size=pos.lot_size,
                limit_price=float(pos.current_price),
                signal_confidence=0.0,
            )

            status = await pipeline._executor.submit_order(close_order)

            pnl = pos.unrealized_pnl
            closed.append({
                "ticker": ticker,
                "direction": pos.direction,
                "lots": pos.lots,
                "entry": pos.entry_price,
                "exit": pos.current_price,
                "pnl": pnl,
                "status": status.value,
            })
            print(f"  {ticker}: {status.value} | P&L {pnl:+,.0f} руб.")

        except Exception as exc:
            failed.append(ticker)
            print(f"  {ticker}: ОШИБКА — {exc}")

    # Telegram уведомление
    total_pnl = sum(t["pnl"] for t in closed)
    tickers_closed = [t["ticker"] for t in closed]

    if pipeline._telegram:
        msg = (
            f"EMERGENCY CLOSE: все позиции закрыты\n"
            f"Закрыто: {len(closed)} позиций: {', '.join(tickers_closed)}\n"
            f"Суммарный P&L: {total_pnl:+,.0f} руб.\n"
            f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if failed:
            msg += f"\nОШИБКИ при закрытии: {', '.join(failed)}"
        try:
            await pipeline._telegram.notify_alert("EMERGENCY", msg)
        except Exception as exc:
            print(f"Telegram: не удалось отправить — {exc}")

    # Итог
    print()
    print("─" * 40)
    print(f"Закрыто позиций:  {len(closed)}")
    if failed:
        print(f"Ошибки:           {len(failed)} ({', '.join(failed)})")
    print(f"Суммарный P&L:    {total_pnl:+,.0f} руб.")
    print("─" * 40)
    print()


if __name__ == "__main__":
    asyncio.run(main())
