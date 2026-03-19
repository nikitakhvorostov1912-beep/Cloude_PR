"""Загрузка данных USD/RUB из MOEX ISS для бэктеста Si-стратегии.

Загружает USD/RUB (USDRUB_TOD / USD000UTSTOM) дневные свечи за 2021-2026
с валютного рынка MOEX (engine=currency, market=selt, board=CETS)
и сохраняет в SQLite как тикер "USDRUB".

Почему валютный рынок, не FORTS:
- Непрерывный ряд без gaps при роллировании контрактов
- Доступна история с 2000-х годов
- Корреляция Si с USDRUB ~0.99 — ряды практически идентичны

Endpoint:
  https://iss.moex.com/iss/engines/currency/markets/selt/boards/CETS
  /securities/USD000UTSTOM/candles.json

Запуск: python -m scripts.load_si_data
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path
from typing import Any

import aiohttp
import structlog

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer(colors=True)],
)
log = structlog.get_logger()

from src.data.db import get_candles, init_db, save_candles
from src.models.market import OHLCVBar

DB_PATH = "data/trading.db"
TICKER = "USDRUB"
FROM_DATE = date(2021, 1, 1)
TO_DATE = date.today()
_PAGE_SIZE = 500
_REQUEST_DELAY = 0.3

# Основной инструмент CETS: USD000UTSTOM (USD/RUB tomorrow)
# Альтернатива: USD000000TOD (USD/RUB today, менее ликвидный)
_SECID = "USD000UTSTOM"
_BASE_URL = "https://iss.moex.com/iss"


def _parse_cets_candles(data: dict[str, Any], ticker: str) -> list[OHLCVBar]:
    """Разобрать ответ ISS /candles.json для валютного рынка.

    Args:
        data: Ответ MOEX ISS в виде словаря.
        ticker: Тикер для сохранения (USDRUB).

    Returns:
        Список OHLCVBar.
    """
    candles_block: dict[str, Any] = data.get("candles", {})
    columns: list[str] = candles_block.get("columns", [])
    rows: list[list[Any]] = candles_block.get("data", [])

    if not columns or not rows:
        return []

    idx = {col: i for i, col in enumerate(columns)}
    result: list[OHLCVBar] = []

    for row in rows:
        try:
            begin_str: str = str(row[idx["begin"]])[:10]
            bar_date = date.fromisoformat(begin_str)

            open_val = float(row[idx["open"]])
            high_val = float(row[idx["high"]])
            low_val = float(row[idx["low"]])
            close_val = float(row[idx["close"]])
            volume_val = int(row[idx["volume"]]) if row[idx["volume"]] is not None else 0
            value_val = float(row[idx["value"]]) if "value" in idx and row[idx["value"]] is not None else None

            # Пропускаем бары с нулевыми ценами
            if open_val <= 0 or close_val <= 0:
                continue

            bar = OHLCVBar(
                ticker=ticker,
                dt=bar_date,
                open=open_val,
                high=max(high_val, open_val, close_val),
                low=min(low_val, open_val, close_val),
                close=close_val,
                volume=volume_val,
                value=value_val,
                source="moex_cets",
            )
            result.append(bar)
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("parse_error", error=str(exc), row=row)

    return result


async def fetch_usdrub_candles(
    from_date: date,
    to_date: date,
    interval: int = 24,
) -> list[OHLCVBar]:
    """Загрузить USD/RUB дневные свечи с MOEX CETS с пагинацией.

    Args:
        from_date: Начальная дата.
        to_date: Конечная дата.
        interval: Интервал в минутах (24 = дневная).

    Returns:
        Список OHLCVBar с ticker="USDRUB".
    """
    url = (
        f"{_BASE_URL}/engines/currency/markets/selt"
        f"/boards/CETS/securities/{_SECID}/candles.json"
    )

    all_bars: list[OHLCVBar] = []
    offset = 0

    async with aiohttp.ClientSession() as session:
        while True:
            params: dict[str, Any] = {
                "from": from_date.isoformat(),
                "till": to_date.isoformat(),
                "interval": interval,
                "start": offset,
            }

            log.debug(
                "fetch_page",
                ticker=TICKER,
                offset=offset,
                from_date=str(from_date),
                to_date=str(to_date),
            )

            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json(content_type=None)

            bars = _parse_cets_candles(data, TICKER)
            all_bars.extend(bars)

            log.debug("page_loaded", offset=offset, bars_in_page=len(bars))

            if len(bars) < _PAGE_SIZE:
                break

            offset += _PAGE_SIZE
            await asyncio.sleep(_REQUEST_DELAY)

    # Удалить дубликаты (по дате), сортировать
    seen: set[str] = set()
    unique_bars: list[OHLCVBar] = []
    for bar in sorted(all_bars, key=lambda b: b.dt):
        key = bar.dt.isoformat()
        if key not in seen:
            seen.add(key)
            unique_bars.append(bar)

    return unique_bars


async def main() -> None:
    """Основной pipeline загрузки USD/RUB данных."""
    Path("data").mkdir(exist_ok=True)

    log.info("init_db", path=DB_PATH)
    await init_db(DB_PATH)

    log.info(
        "loading_usdrub",
        ticker=TICKER,
        secid=_SECID,
        from_date=str(FROM_DATE),
        to_date=str(TO_DATE),
    )

    try:
        bars = await fetch_usdrub_candles(FROM_DATE, TO_DATE)
    except aiohttp.ClientError as exc:
        log.error("fetch_failed", error=str(exc))
        raise

    if not bars:
        log.error("no_data_received", ticker=TICKER, secid=_SECID)
        return

    log.info("fetched", ticker=TICKER, bars=len(bars))

    saved = await save_candles(DB_PATH, bars)
    log.info("saved", ticker=TICKER, records=saved)

    # Проверка загруженных данных
    loaded = await get_candles(DB_PATH, TICKER, FROM_DATE, TO_DATE)
    if loaded:
        log.info(
            "data_check",
            ticker=TICKER,
            total_bars=len(loaded),
            first_date=str(loaded[0].dt),
            last_date=str(loaded[-1].dt),
            first_close=loaded[0].close,
            last_close=loaded[-1].close,
            min_close=min(b.close for b in loaded),
            max_close=max(b.close for b in loaded),
        )
    else:
        log.warning("data_check_failed", ticker=TICKER)

    log.info("load_si_data.done", ticker=TICKER, bars_saved=saved)


if __name__ == "__main__":
    asyncio.run(main())
