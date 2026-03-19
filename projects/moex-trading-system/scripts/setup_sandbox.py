"""Настройка Tinkoff Invest Sandbox.

Скрипт выполняет:
1. Читает TINKOFF_TOKEN из .env
2. Открывает Sandbox account (или переиспользует существующий)
3. Пополняет 1 000 000 виртуальных рублей
4. Проверяет список позиций (должен быть пустым)
5. Проверяет работоспособность API: запрашивает цену SBER
6. Сохраняет account_id в .env (добавляет/обновляет TINKOFF_ACCOUNT_ID)

Запуск:
    python scripts/setup_sandbox.py

Требования:
    TINKOFF_TOKEN должен быть задан в .env (sandbox-токен из личного кабинета Tinkoff Invest)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для импортов src.*
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv

# Загружаем .env
_env_path = _project_root / ".env"
load_dotenv(_env_path, override=True)

import os
import structlog
import logging

# ─── Настройка логирования ────────────────────────────────────────────────────

logging.basicConfig(format="%(message)s", level=logging.INFO)
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("setup_sandbox")

# ─── Утилиты ─────────────────────────────────────────────────────────────────


def update_env_file(env_path: Path, key: str, value: str) -> None:
    """Добавить или обновить переменную в .env файле."""
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)

    if pattern.search(content):
        new_content = pattern.sub(f"{key}={value}", content)
    else:
        # Добавляем в конец файла
        new_content = content.rstrip("\n") + f"\n{key}={value}\n"

    env_path.write_text(new_content, encoding="utf-8")
    logger.info("env.updated", key=key, file=str(env_path))


# ─── Основная логика ─────────────────────────────────────────────────────────


def setup_sandbox() -> None:
    """Полная настройка Tinkoff Sandbox."""
    logger.info("setup_sandbox.start")

    # 1. Читаем токен
    token = os.getenv("TINKOFF_TOKEN", "").strip()
    if not token:
        logger.error("setup_sandbox.no_token", hint="Задайте TINKOFF_TOKEN в .env файле")
        sys.exit(1)
    if token.startswith("t.") is False and len(token) < 20:
        logger.warning(
            "setup_sandbox.suspicious_token",
            hint="Токен должен начинаться с 't.' — проверьте что используете sandbox-токен",
        )
    logger.info("setup_sandbox.token_found", token_prefix=token[:8] + "***")

    # 2. Открываем Sandbox account
    logger.info("setup_sandbox.opening_account")
    from t_tech.invest.sandbox.client import SandboxClient
    from t_tech.invest import MoneyValue

    account_id: str | None = None

    with SandboxClient(token) as client:
        # Проверяем существующие аккаунты
        existing = client.sandbox.get_sandbox_accounts().accounts
        if existing:
            account_id = existing[0].id
            logger.info("setup_sandbox.reuse_account", account_id=account_id, total=len(existing))
        else:
            response = client.sandbox.open_sandbox_account()
            account_id = response.account_id
            logger.info("setup_sandbox.account_opened", account_id=account_id)

        # 3. Пополняем виртуальный счёт
        logger.info("setup_sandbox.funding", amount=1_000_000, currency="RUB")
        client.sandbox.sandbox_pay_in(
            account_id=account_id,
            amount=MoneyValue(currency="rub", units=1_000_000, nano=0),
        )
        logger.info("setup_sandbox.funded", status="OK")

        # 4. Проверяем позиции (должны быть пустыми)
        positions_response = client.sandbox.get_sandbox_positions(account_id=account_id)
        securities_count = len([s for s in positions_response.securities if s.balance != 0])
        logger.info(
            "setup_sandbox.positions_check",
            securities=securities_count,
            status="empty" if securities_count == 0 else "has_positions",
        )

        # 5. Проверяем API: запрашиваем цену SBER
        logger.info("setup_sandbox.api_check", ticker="SBER")
        from t_tech.invest import InstrumentIdType

        try:
            instrument_response = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                class_code="TQBR",
                id="SBER",
            )
            sber_figi = instrument_response.instrument.figi
            sber_lot = instrument_response.instrument.lot
            logger.info("setup_sandbox.sber_found", figi=sber_figi, lot=sber_lot)

            # Запрашиваем последнюю цену
            price_response = client.market_data.get_last_prices(figi=[sber_figi])
            if price_response.last_prices:
                from src.execution.tinkoff_adapter import quotation_to_float

                sber_price = quotation_to_float(price_response.last_prices[0].price)
                logger.info("setup_sandbox.sber_price", price=sber_price, currency="RUB")

                if sber_price > 0:
                    logger.info("setup_sandbox.api_check.PASS", ticker="SBER", price=sber_price)
                else:
                    logger.warning(
                        "setup_sandbox.api_check.WARN",
                        msg="Цена SBER = 0 — возможно биржа закрыта или sandbox ограничен",
                    )
            else:
                logger.warning("setup_sandbox.api_check.no_price", ticker="SBER")

        except Exception as exc:
            logger.warning("setup_sandbox.api_check.error", error=str(exc))

        # Показываем баланс портфеля
        try:
            portfolio = client.sandbox.get_sandbox_portfolio(account_id=account_id)
            from src.execution.tinkoff_adapter import moneyvalue_to_float

            total = moneyvalue_to_float(portfolio.total_amount_portfolio)
            currencies = moneyvalue_to_float(portfolio.total_amount_currencies)
            logger.info(
                "setup_sandbox.portfolio",
                total_portfolio=round(total, 2),
                cash_rub=round(currencies, 2),
            )
        except Exception as exc:
            logger.warning("setup_sandbox.portfolio_error", error=str(exc))

    # 6. Сохраняем account_id в .env
    if account_id:
        update_env_file(_env_path, "TINKOFF_ACCOUNT_ID", account_id)
        logger.info(
            "setup_sandbox.complete",
            account_id=account_id,
            env_file=str(_env_path),
        )
    else:
        logger.error("setup_sandbox.no_account_id")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Tinkoff Sandbox готов к работе!")
    print(f"  Account ID: {account_id}")
    print(f"  Баланс: 1,000,000 RUB (виртуальные)")
    print(f"  TINKOFF_ACCOUNT_ID сохранён в {_env_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    setup_sandbox()
