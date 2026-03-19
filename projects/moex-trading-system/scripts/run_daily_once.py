"""Быстрый запуск одного дневного цикла торговой системы.

Обёртка над TradingPipeline.run_daily_cycle().
Используется для ручного тестирования и отладки без планировщика.

Запуск:
    cd C:\\CLOUDE_PR\\projects\\moex-trading-system
    venv\\Scripts\\python.exe scripts/run_daily_once.py

    # С подробным выводом:
    venv\\Scripts\\python.exe scripts/run_daily_once.py --verbose

    # Только анализ, без исполнения:
    venv\\Scripts\\python.exe scripts/run_daily_once.py --dry-run
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings  # noqa: E402
from src.data.db import init_db  # noqa: E402
from src.main import TradingPipeline, configure_logging  # noqa: E402


async def run_once(verbose: bool = False, dry_run: bool = False) -> None:
    """Запустить один полный дневной цикл.

    Args:
        verbose: Включить DEBUG-логирование.
        dry_run: Пропустить шаги execute и отправку в Telegram.
    """
    settings = get_settings()
    log_level = "DEBUG" if verbose else settings.log_level
    configure_logging(log_level)

    # Инициализация БД
    settings.db_path_resolved.parent.mkdir(parents=True, exist_ok=True)
    await init_db(str(settings.db_path_resolved))

    pipeline = TradingPipeline()

    if dry_run:
        # В dry-run режиме: только загрузка данных + анализ, без исполнения
        print("=== DRY-RUN MODE: только загрузка данных и анализ ===\n")

        data = await pipeline.step_load_data()
        print(f"[1/2] Данные загружены: {data['bars_loaded']} баров, {data['news_count']} новостей")
        print(f"      Макро: {list(data.get('macro', {}).keys())}")

        analysis = await pipeline.step_analyze(data)
        regime = analysis.get("regime")
        pre_scores = analysis.get("pre_scores", {})

        print(f"\n[2/2] Анализ завершён: режим рынка = {regime.value if regime else 'unknown'}")
        print("\nPre-Scores (топ-10):")

        sorted_scores = sorted(pre_scores.items(), key=lambda x: x[1], reverse=True)
        for ticker, score in sorted_scores[:10]:
            threshold_marker = " ← PASS (>= 45)" if score >= 45.0 else ""
            print(f"  {ticker:6s} : {score:6.1f}{threshold_marker}")

        print("\nЗапускать полный цикл: python scripts/run_daily_once.py")
        return

    # Полный цикл
    result = await pipeline.run_daily_cycle()

    # Красивый вывод результатов
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ ДНЕВНОГО ЦИКЛА")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))
    print("=" * 60)

    # Краткая сводка
    steps = result.get("steps", {})
    print("\nКРАТКАЯ СВОДКА:")
    print(f"  Дата:          {result.get('date')}")
    print(f"  Время:         {result.get('elapsed_seconds')}с")

    if "load_data" in steps:
        ld = steps["load_data"]
        print(f"  Баров:         {ld.get('bars_loaded', 0)}")
        print(f"  Новостей:      {ld.get('news_count', 0)}")

    if "analyze" in steps:
        an = steps["analyze"]
        print(f"  Режим рынка:   {an.get('regime', 'unknown')}")
        print(f"  Тикеров:       {an.get('tickers_analyzed', 0)}")
        ps = an.get("pre_scores", {})
        above = sum(1 for s in ps.values() if s >= 45)
        print(f"  Pre-Score≥45:  {above}")

    if "generate_signals" in steps:
        gs = steps["generate_signals"]
        print(f"  Сигналов:      {gs.get('signals_count', 0)}")

    if "execute" in steps:
        ex = steps["execute"]
        print(f"  Исполнено:     {ex.get('filled', 0)}")
        print(f"  Отклонено:     {ex.get('rejected', 0)}")

    if "error" in result:
        print(f"\n  ОШИБКА: {result['error']}")


def main() -> None:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    dry_run = "--dry-run" in sys.argv or "--dry" in sys.argv

    asyncio.run(run_once(verbose=verbose, dry_run=dry_run))


if __name__ == "__main__":
    main()
