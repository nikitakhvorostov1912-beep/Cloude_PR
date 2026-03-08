"""Конфигурация Voice Agent для 1С франшизы.

Загружает настройки из переменных окружения (.env файл).
"""
from __future__ import annotations

import functools

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MangoSettings(BaseSettings):
    """Настройки Манго Офис телефонии."""

    model_config = SettingsConfigDict(env_prefix="MANGO_")

    api_key: str = Field(default="", description="API ключ Манго Офис")
    api_salt: str = Field(default="", description="Соль для подписи")
    webhook_secret: str = Field(default="", description="Секрет для проверки вебхуков")


class OneCSettings(BaseSettings):
    """Настройки подключения к 1С."""

    model_config = SettingsConfigDict(env_prefix="ONEC_")

    base_url: str = Field(
        default="http://localhost/api/v1", description="Базовый URL 1С API"
    )
    username: str = Field(default="", description="Логин Basic Auth")
    password: str = Field(default="", description="Пароль Basic Auth")
    timeout: float = Field(default=5.0, description="Таймаут запроса (сек)")
    max_retries: int = Field(default=3, description="Максимум повторов")


class DatabaseSettings(BaseSettings):
    """Настройки PostgreSQL / SQLite."""

    model_config = SettingsConfigDict(populate_by_name=True, env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://voice_agent:voice_agent@localhost:5432/voice_agent",
        alias="DATABASE_URL",
    )


class RedisSettings(BaseSettings):
    """Настройки Redis / FakeRedis."""

    model_config = SettingsConfigDict(populate_by_name=True, env_file=".env", env_file_encoding="utf-8", extra="ignore")

    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")


class YandexSettings(BaseSettings):
    """Настройки Yandex SpeechKit (STT + TTS)."""

    model_config = SettingsConfigDict(env_prefix="YANDEX_")

    api_key: str = Field(default="", description="IAM-токен или API-ключ Yandex Cloud")
    folder_id: str = Field(default="", description="ID каталога Yandex Cloud")

    # STT
    stt_model: str = Field(default="general:rc", description="Модель распознавания")
    stt_language: str = Field(default="ru-RU", description="Язык распознавания")
    stt_sample_rate: int = Field(default=8000, description="Частота дискретизации (Гц)")
    stt_silence_threshold_ms: int = Field(
        default=800, description="Порог тишины для VAD (мс)"
    )

    # TTS
    tts_voice: str = Field(default="alena", description="Голос TTS")
    tts_speed: float = Field(default=1.0, description="Скорость речи")
    tts_emotion: str = Field(default="neutral", description="Эмоция голоса")
    tts_sample_rate: int = Field(default=8000, description="Частота дискретизации TTS")


class AISettings(BaseSettings):
    """Настройки Claude AI Agent."""

    model_config = SettingsConfigDict(populate_by_name=True)

    api_key: str = Field(default="", alias="ANTHROPIC_API_KEY", description="Anthropic API ключ")
    model: str = Field(
        default="claude-sonnet-4-20250514", alias="AI_MODEL", description="Модель Claude"
    )
    max_tokens: int = Field(default=1024, alias="AI_MAX_TOKENS", description="Макс. токенов в ответе")
    max_questions: int = Field(
        default=5, description="Макс. вопросов за диалог"
    )
    confidence_threshold: float = Field(
        default=0.65, description="Порог уверенности для уточнения"
    )
    temperature: float = Field(default=0.3, description="Температура генерации")


class AppSettings(BaseSettings):
    """Главные настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_title: str = Field(default="Voice Agent 1C")
    app_version: str = Field(default="0.2.0")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    allowed_origins: list[str] = Field(
        default_factory=list,
        alias="ALLOWED_ORIGINS",
        description="CORS origins через запятую. Пусто = localhost:3000",
    )

    mango: MangoSettings = Field(default_factory=MangoSettings)
    onec: OneCSettings = Field(default_factory=OneCSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    yandex: YandexSettings = Field(default_factory=YandexSettings)
    ai: AISettings = Field(default_factory=AISettings)


@functools.lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Загружает и кеширует настройки приложения."""
    return AppSettings()
