"""Yandex SpeechKit TTS service with SSML support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from orchestrator.config import YandexSettings

logger = logging.getLogger(__name__)

YANDEX_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


@dataclass(frozen=True)
class TTSResult:
    audio_data: bytes
    duration_ms: float
    text: str
    sample_rate: int = 8000


class YandexTTSService:
    """Text-to-speech via Yandex SpeechKit REST API."""

    def __init__(self, settings: YandexSettings) -> None:
        self._settings = settings

    async def synthesize(
        self, text: str, *, ssml: bool = False
    ) -> Optional[TTSResult]:
        if not self._settings.api_key:
            logger.debug("TTS: no API key, skipping synthesis")
            return None

        data = {
            "folderId": self._settings.folder_id,
            "voice": self._settings.tts_voice,
            "speed": str(self._settings.tts_speed),
            "emotion": self._settings.tts_emotion,
            "format": "lpcm",
            "sampleRateHertz": str(self._settings.tts_sample_rate),
        }
        if ssml:
            data["ssml"] = text
        else:
            data["text"] = text

        headers = {"Authorization": f"Api-Key {self._settings.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    YANDEX_TTS_URL, data=data, headers=headers
                )
                response.raise_for_status()
                audio = response.content
                duration_ms = (
                    len(audio) / (self._settings.tts_sample_rate * 2) * 1000
                )
                return TTSResult(
                    audio_data=audio,
                    duration_ms=duration_ms,
                    text=text,
                    sample_rate=self._settings.tts_sample_rate,
                )
        except Exception:
            logger.exception("TTS synthesis failed")
            return None

    def build_greeting_ssml(
        self, client_name: Optional[str] = None
    ) -> str:
        name = self._sanitize(client_name) if client_name else None
        if name:
            return (
                f'<speak>Здравствуйте, {name}.'
                f' <break time="300ms"/>'
                f' Чем могу помочь?</speak>'
            )
        return (
            '<speak>Здравствуйте!'
            ' <break time="300ms"/>'
            ' Вы позвонили в службу поддержки.'
            ' Чем могу помочь?</speak>'
        )

    def build_farewell_ssml(self, task_number: Optional[str] = None) -> str:
        if task_number:
            return (
                f'<speak>Задача номер {task_number} создана.'
                f' <break time="200ms"/>'
                f' Специалист свяжется с вами. Всего доброго!</speak>'
            )
        return '<speak>Спасибо за обращение. Всего доброго!</speak>'

    @staticmethod
    def _sanitize(text: str) -> str:
        return text.replace("\n", " ").replace("\r", " ").strip()[:100]
