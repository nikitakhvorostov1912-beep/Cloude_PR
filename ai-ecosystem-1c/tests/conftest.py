"""Shared fixtures for all tests."""

from __future__ import annotations

import pytest

from orchestrator.config import (
    AISettings,
    AppSettings,
    MangoSettings,
    OneCSettings,
    SakuraSettings,
    SMSSettings,
    TelegramSettings,
    YandexSettings,
)


@pytest.fixture
def app_settings() -> AppSettings:
    """AppSettings for testing — all defaults, dev mode."""
    return AppSettings()


@pytest.fixture
def yandex_settings() -> YandexSettings:
    return YandexSettings(api_key="test-key", folder_id="test-folder")


@pytest.fixture
def ai_settings() -> AISettings:
    return AISettings(api_key="test-anthropic-key")


@pytest.fixture
def mango_settings() -> MangoSettings:
    return MangoSettings(webhook_secret="test-secret")


@pytest.fixture
def onec_settings() -> OneCSettings:
    return OneCSettings(base_url="http://localhost:8080/test")


@pytest.fixture
def sakura_settings() -> SakuraSettings:
    return SakuraSettings(base_url="http://localhost:9090/test", api_key="test-key")


@pytest.fixture
def sms_settings() -> SMSSettings:
    return SMSSettings(login="test", password="test")


@pytest.fixture
def telegram_settings() -> TelegramSettings:
    return TelegramSettings(bot_token="test-token", admin_chat_id="123")
