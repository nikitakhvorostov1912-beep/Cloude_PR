"""Загрузка исторических данных MOEX для бэктестинга.

Загружает OHLCV за 3 года для всех тикеров из watchlist + IMOEX индекс.
Сохраняет в SQLite базу.

Запуск: python -m scripts.load_historical_data
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

# Добавить корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.db import init_db, save_candles, get_candles
from src.data.moex_client import fetch_candles, fetch_index, fetch_instruments
from src.data.macro_fetcher import fetch_all_macro, fetch_cbr_key_rate, fetch_usd_rub

import structlog

structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(colors=True),
    ],
)
log = structlog.get_logger()

DB_PATH = "data/trading.db"
TICKERS = ["SBER", "GAZP", "LKOH", "YDEX", "NVTK", "ROSN", "GMKN", "VTBR", "MGNT", "MTSS"]
FROM_DATE = date(2021, 1, 1)
TO_DATE = date.today()


async def load_ticker_candles(ticker: str) -> int:
    """Загрузить свечи для одного тикера."""
    log.info("loading_candles", ticker=ticker, from_date=str(FROM_DATE), to_date=str(TO_DATE))
    try:
        candles = await fetch_candles(ticker, FROM_DATE, TO_DATE, interval=24)
        if candles:
            saved = await save_candles(DB_PATH, candles)
            log.info("candles_saved", ticker=ticker, count=saved)
            return saved
        else:
            log.warning("no_candles", ticker=ticker)
            return 0
    except Exception as e:
        log.error("candles_error", ticker=ticker, error=str(e))
        return 0


async def load_index() -> int:
    """Загрузить данные индекса IMOEX."""
    log.info("loading_index", index="IMOEX")
    try:
        candles = await fetch_index("IMOEX", FROM_DATE, TO_DATE)
        if candles:
            saved = await save_candles(DB_PATH, candles)
            log.info("index_saved", index="IMOEX", count=saved)
            return saved
        else:
            log.warning("no_index_data")
            return 0
    except Exception as e:
        log.error("index_error", error=str(e))
        return 0


async def load_macro() -> dict[str, float]:
    """Загрузить макроданные."""
    log.info("loading_macro")
    try:
        macro = await fetch_all_macro()
        log.info("macro_loaded", data=macro)
        return macro
    except Exception as e:
        log.error("macro_error", error=str(e))
        return {}


async def main() -> None:
    """Основной pipeline загрузки данных."""
    # Создать директорию data/ если нет
    Path("data").mkdir(exist_ok=True)

    # Инициализировать БД
    log.info("init_db", path=DB_PATH)
    await init_db(DB_PATH)

    # Загрузить свечи по всем тикерам (последовательно, чтобы не превысить rate limit)
    total_candles = 0
    for ticker in TICKERS:
        count = await load_ticker_candles(ticker)
        total_candles += count
        await asyncio.sleep(0.5)  # пауза между тикерами

    # Загрузить индекс IMOEX
    index_count = await load_index()

    # Загрузить макроданные
    macro = await load_macro()

    # Проверить что данные загружены
    log.info("=" * 60)
    log.info("data_loading_complete",
             tickers=len(TICKERS),
             total_candles=total_candles,
             index_candles=index_count,
             macro_indicators=len(macro))

    # Показать статистику по каждому тикеру
    for ticker in TICKERS:
        candles = await get_candles(DB_PATH, ticker, FROM_DATE, TO_DATE)
        if candles:
            log.info("ticker_stats",
                     ticker=ticker,
                     bars=len(candles),
                     first=str(candles[0].dt),
                     last=str(candles[-1].dt),
                     last_close=candles[-1].close)
        else:
            log.warning("no_data", ticker=ticker)


if __name__ == "__main__":
    asyncio.run(main())
