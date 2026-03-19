"""Paper Trading Scheduler — автоматический ежедневный запуск.

Расписание (Europe/Moscow):
    06:30 пн-пт — полный торговый цикл
    10:00-18:55 пн-пт — мониторинг позиций каждые 5 минут
    19:00 пн-пт — дневной отчёт

Логирование: structlog + файл data/logs/trading_YYYY-MM-DD.log
Остановка: Ctrl+C (graceful shutdown).
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Загрузка .env из корня проекта
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(_PROJECT_ROOT))

# Fix Windows cp1251 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

import structlog  # noqa: E402

from src.main import TradingPipeline, configure_logging  # noqa: E402

logger = structlog.get_logger(__name__)

_TZ = "Europe/Moscow"


def _setup_file_logging() -> None:
    """Добавить FileHandler к root-логгеру для записи в data/logs/."""
    log_dir = _PROJECT_ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"trading_{datetime.now().strftime('%Y-%m-%d')}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    print(f"Логирование: {log_file}")


async def main() -> None:
    """Точка входа планировщика."""
    configure_logging("INFO")
    _setup_file_logging()

    pipeline = TradingPipeline()
    scheduler = AsyncIOScheduler(timezone=_TZ)

    # ── Задание 1: Утренний торговый цикл (06:30 MSK, пн-пт) ──────────────
    scheduler.add_job(
        pipeline.run_daily_cycle,
        CronTrigger(hour=6, minute=30, day_of_week="mon-fri", timezone=_TZ),
        id="daily_cycle",
        name="Утренний торговый цикл",
        misfire_grace_time=300,  # 5 минут допуск при задержке запуска
    )

    # ── Задание 2: Мониторинг позиций (каждые 5 мин, 10:00-18:55, пн-пт) ──
    scheduler.add_job(
        pipeline.step_monitor,
        CronTrigger(minute="*/5", hour="10-18", day_of_week="mon-fri", timezone=_TZ),
        id="monitor",
        name="Мониторинг позиций",
        misfire_grace_time=60,
    )

    # ── Задание 3: Дневной отчёт (19:00 MSK, пн-пт) ───────────────────────
    scheduler.add_job(
        pipeline.step_daily_report,
        CronTrigger(hour=19, minute=0, day_of_week="mon-fri", timezone=_TZ),
        id="daily_report",
        name="Дневной отчёт",
        misfire_grace_time=600,
    )

    scheduler.start()
    logger.info("scheduler.started", jobs=len(scheduler.get_jobs()))

    _mode = pipeline._settings.trading_mode
    _tickers_count = len(pipeline._ticker_symbols)
    _telegram_on = pipeline._telegram is not None

    print("=" * 60)
    print("  MOEX Trading System — Paper Trading Mode")
    print(f"  Запущен:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Режим:    {_mode}")
    print(f"  Тикеры:   {_tickers_count}")
    print(f"  Telegram: {'Включён' if _telegram_on else 'Выключен'}")
    print("  Расписание:")
    print("    06:30 MSK — Торговый цикл (пн-пт)")
    print("    10:00-19:00 — Мониторинг каждые 5 мин")
    print("    19:00 MSK — Дневной отчёт")
    print("  Ctrl+C для остановки")
    print("=" * 60)

    # ── Ожидание сигнала завершения ────────────────────────────────────────
    stop_event = asyncio.Event()

    def _on_signal(sig: int, frame: object) -> None:
        print(f"\nПолучен сигнал {sig}, остановка...")
        stop_event.set()

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    await stop_event.wait()

    scheduler.shutdown(wait=False)
    logger.info("scheduler.stopped")
    print("Система остановлена.")


if __name__ == "__main__":
    asyncio.run(main())
