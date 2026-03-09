"""Centralised application configuration via Pydantic Settings v2.

Every config section is an isolated ``BaseSettings`` subclass with its own
``env_prefix`` so environment variables never collide.  The top-level
``AppSettings`` aggregates them all and is cached as a process-wide singleton.
"""

from __future__ import annotations

import functools
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ──────────────────────────────────────────────────────────────────────
# Telephony — Mango Office
# ──────────────────────────────────────────────────────────────────────
class MangoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MANGO_")

    api_key: str = Field(default="", description="Mango Office API key")
    api_salt: str = Field(default="", description="Salt for HMAC signature")
    webhook_secret: str = Field(default="", description="Webhook validation secret")


# ──────────────────────────────────────────────────────────────────────
# 1С HTTP-service
# ──────────────────────────────────────────────────────────────────────
class OneCSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ONEC_")

    base_url: str = Field(default="http://localhost:8080/base/hs/api/v1")
    username: str = Field(default="")
    password: str = Field(default="")
    timeout_sec: float = Field(default=5.0)
    max_retries: int = Field(default=3)


# ──────────────────────────────────────────────────────────────────────
# Sakura CRM
# ──────────────────────────────────────────────────────────────────────
class SakuraSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAKURA_")

    base_url: str = Field(default="http://localhost:9090/api/v1")
    api_key: str = Field(default="")
    timeout_sec: float = Field(default=5.0)


# ──────────────────────────────────────────────────────────────────────
# Yandex SpeechKit (STT + TTS)
# ──────────────────────────────────────────────────────────────────────
class YandexSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YANDEX_")

    api_key: str = Field(default="")
    folder_id: str = Field(default="")

    # STT
    stt_model: str = Field(default="general")
    stt_language: str = Field(default="ru-RU")
    stt_sample_rate: int = Field(default=8000)
    stt_silence_threshold_ms: int = Field(default=800)

    # TTS
    tts_voice: str = Field(default="filipp")
    tts_speed: float = Field(default=1.0)
    tts_emotion: str = Field(default="neutral")
    tts_sample_rate: int = Field(default=8000)


# ──────────────────────────────────────────────────────────────────────
# LLM — Anthropic Claude
# ──────────────────────────────────────────────────────────────────────
class AISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_")

    api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    model: str = Field(default="claude-sonnet-4-20250514")
    max_tokens: int = Field(default=1500)
    temperature: float = Field(default=0.1)
    timeout_sec: float = Field(default=10.0)
    max_questions: int = Field(default=5)
    confidence_threshold: float = Field(default=0.65)


# ──────────────────────────────────────────────────────────────────────
# Persistence
# ──────────────────────────────────────────────────────────────────────
class DatabaseSettings(BaseSettings):
    url: str = Field(
        default="sqlite+aiosqlite:///./dev.db",
        alias="DATABASE_URL",
    )
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)
    echo: bool = Field(default=False)


class RedisSettings(BaseSettings):
    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    call_session_ttl: int = Field(default=1800, description="30 min in seconds")
    client_cache_ttl: int = Field(default=86400, description="24 h in seconds")


# ──────────────────────────────────────────────────────────────────────
# Qdrant (vector DB, Phase 2)
# ──────────────────────────────────────────────────────────────────────
class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    host: str = Field(default="localhost")
    port: int = Field(default=6333)
    api_key: str = Field(default="")


# ──────────────────────────────────────────────────────────────────────
# Notifications
# ──────────────────────────────────────────────────────────────────────
class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEGRAM_")

    bot_token: str = Field(default="")
    admin_chat_id: str = Field(default="")


class SMSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SMSC_")

    login: str = Field(default="")
    password: str = Field(default="")
    sender_name: str = Field(default="1C-Company", alias="SMS_SENDER_NAME")


# ──────────────────────────────────────────────────────────────────────
# Application-level
# ──────────────────────────────────────────────────────────────────────
class AppSettings(BaseSettings):
    env: Literal["development", "staging", "production"] = Field(
        default="development", alias="APP_ENV",
    )
    log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    secret_key: str = Field(default="change-me", alias="APP_SECRET_KEY")
    working_hours_start: str = Field(default="09:00", alias="WORKING_HOURS_START")
    working_hours_end: str = Field(default="19:00", alias="WORKING_HOURS_END")
    working_timezone: str = Field(default="Europe/Moscow", alias="WORKING_TIMEZONE")
    deduplication_window_minutes: int = Field(default=30)
    escalation_confidence_threshold: float = Field(default=0.65)
    low_confidence_flag_threshold: float = Field(default=0.80)

    # Nested settings
    mango: MangoSettings = Field(default_factory=MangoSettings)
    onec: OneCSettings = Field(default_factory=OneCSettings)
    sakura: SakuraSettings = Field(default_factory=SakuraSettings)
    yandex: YandexSettings = Field(default_factory=YandexSettings)
    ai: AISettings = Field(default_factory=AISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    sms: SMSSettings = Field(default_factory=SMSSettings)

    @property
    def is_dev(self) -> bool:
        return self.env == "development"

    @property
    def is_prod(self) -> bool:
        return self.env == "production"


@functools.cache
def get_settings() -> AppSettings:
    """Cached singleton — parsed once per process."""
    return AppSettings()
