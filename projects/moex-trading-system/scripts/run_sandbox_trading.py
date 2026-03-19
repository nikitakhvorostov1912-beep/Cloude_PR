"""Запуск торговли в Tinkoff Sandbox.

Обёртка над Daily Pipeline Runner с TinkoffExecutor вместо PaperExecutor.

Выполняет один торговый цикл и показывает:
- Какие сигналы сгенерированы
- Какие ордера выставлены в Sandbox
- Текущий портфель после цикла

Запуск:
    python scripts/run_sandbox_trading.py

Требования в .env:
    ANTHROPIC_API_KEY  — ключ Claude API
    TINKOFF_TOKEN      — sandbox-токен Tinkoff
    TINKOFF_ACCOUNT_ID — ID sandbox-аккаунта (после setup_sandbox.py)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv

_env_path = _project_root / ".env"
load_dotenv(_env_path, override=True)

import os
import logging
import structlog

# ─── Настройка логирования ────────────────────────────────────────────────────

logging.basicConfig(format="%(message)s", level=logging.INFO)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("run_sandbox_trading")

# ─── Monkey-patch TradingPipeline для Sandbox ─────────────────────────────────


def _patch_pipeline_for_sandbox(pipeline: "TradingPipeline", executor: "TinkoffExecutor") -> None:
    """Заменяем PaperExecutor на TinkoffExecutor в уже созданном pipeline."""
    pipeline._executor = executor
    logger.info("pipeline.executor_patched", mode="sandbox")


# ─── Отображение результатов ─────────────────────────────────────────────────


async def _show_sandbox_results(executor: "TinkoffExecutor") -> None:
    """Показать итоговое состояние sandbox после торгового цикла."""
    print("\n" + "=" * 70)
    print("  РЕЗУЛЬТАТЫ SANDBOX ТОРГОВОГО ЦИКЛА")
    print("=" * 70)

    try:
        portfolio = await executor.get_portfolio()
        print(f"\n  Портфель:")
        print(f"    Кэш (RUB):        {portfolio.cash:>15,.2f}")
        print(f"    Акции (RUB):      {portfolio.total_market_value:>15,.2f}")
        print(f"    Итого (equity):   {portfolio.equity:>15,.2f}")
        print(f"    Позиций открыто:  {len(portfolio.positions)}")

        if portfolio.positions:
            print(f"\n  Открытые позиции:")
            for ticker, pos in portfolio.positions.items():
                pnl = pos.unrealized_pnl
                pnl_sign = "+" if pnl >= 0 else ""
                print(
                    f"    {ticker:<8} {pos.direction:<5} "
                    f"{pos.lots} лот(ов) x {pos.lot_size} шт = {pos.shares} акций  "
                    f"цена: {pos.current_price:.2f}  "
                    f"P&L: {pnl_sign}{pnl:,.2f} RUB"
                )
    except Exception as exc:
        print(f"  Ошибка получения портфеля: {exc}")

    print("=" * 70 + "\n")


# ─── Основная логика ─────────────────────────────────────────────────────────


async def run_sandbox_trading() -> None:
    """Запустить один цикл торговой системы в Sandbox режиме."""
    logger.info("run_sandbox_trading.start")

    # Проверка токенов
    tinkoff_token = os.getenv("TINKOFF_TOKEN", "").strip()
    if not tinkoff_token:
        logger.error("run_sandbox_trading.no_token", hint="Запустите сначала scripts/setup_sandbox.py")
        sys.exit(1)

    tinkoff_account_id = os.getenv("TINKOFF_ACCOUNT_ID", "").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    if not anthropic_key:
        logger.error("run_sandbox_trading.no_anthropic_key")
        sys.exit(1)

    logger.info(
        "run_sandbox_trading.config",
        tinkoff_token_prefix=tinkoff_token[:8] + "***",
        account_id=tinkoff_account_id or "будет получен автоматически",
    )

    # Импортируем после загрузки .env
    from src.execution.tinkoff_adapter import TinkoffExecutor
    from src.main import TradingPipeline, configure_logging
    from src.config import get_settings

    settings = get_settings()
    configure_logging(settings.log_level)

    # 1. Инициализируем TinkoffExecutor
    logger.info("sandbox.executor.init")
    executor = TinkoffExecutor(token=tinkoff_token, mode="sandbox")

    # Если account_id уже известен — используем его, иначе setup создаст новый
    if tinkoff_account_id:
        executor._account_id = tinkoff_account_id
        logger.info("sandbox.executor.account_set", account_id=tinkoff_account_id)
    else:
        logger.info("sandbox.executor.setup_start")
        account_id = await executor.setup()
        logger.info("sandbox.executor.setup_done", account_id=account_id)

    # 2. Создаём TradingPipeline (с PaperExecutor по умолчанию)
    logger.info("sandbox.pipeline.init")
    pipeline = TradingPipeline()

    # 3. Подменяем executor на TinkoffExecutor
    _patch_pipeline_for_sandbox(pipeline, executor)

    # 4. Показываем начальное состояние портфеля
    logger.info("sandbox.portfolio.initial")
    try:
        initial_portfolio = await executor.get_portfolio()
        logger.info(
            "sandbox.portfolio.snapshot",
            cash=round(initial_portfolio.cash, 2),
            equity=round(initial_portfolio.equity, 2),
            positions=len(initial_portfolio.positions),
        )
    except Exception as exc:
        logger.warning("sandbox.portfolio.initial_error", error=str(exc))

    # 5. Запускаем один цикл pipeline
    logger.info("sandbox.pipeline.run_once.start")
    print("\n" + "=" * 70)
    print("  Запуск торгового цикла в Tinkoff Sandbox...")
    print("=" * 70 + "\n")

    try:
        # Запускаем полный дневной цикл через run_daily_cycle
        logger.info("sandbox.run_daily_cycle")
        result = await pipeline.run_daily_cycle()

        exec_data = result.get("steps", {}).get("execute", {})
        logger.info(
            "sandbox.pipeline.complete",
            orders_submitted=exec_data.get("submitted", 0),
            orders_filled=exec_data.get("filled", 0),
        )

    except AttributeError as exc:
        # Если pipeline не имеет нужных методов — запускаем базовый цикл
        logger.warning(
            "sandbox.pipeline.fallback",
            error=str(exc),
            hint="Используем run_once() как fallback",
        )
        await pipeline.run_once()

    except Exception as exc:
        logger.error("sandbox.pipeline.error", error=str(exc), exc_info=True)
        print(f"\n  ОШИБКА в торговом цикле: {exc}")
        print("  Проверьте логи выше для деталей.\n")

    # 6. Показываем итоговые результаты
    await _show_sandbox_results(executor)

    logger.info("run_sandbox_trading.done")


if __name__ == "__main__":
    # Windows event loop policy fix
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run_sandbox_trading())
