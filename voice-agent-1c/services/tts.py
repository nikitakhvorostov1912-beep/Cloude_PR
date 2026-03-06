"""Yandex SpeechKit TTS — синтез речи.

REST API: POST https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize

Голос: alena (русский, профессиональный)
Формат: lpcm 8kHz 16-bit mono (совместимо с телефонией)
Поддержка SSML для пауз и ударений.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

TTS_API_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


@dataclass
class TTSResult:
    """Результат синтеза речи."""

    audio_data: bytes
    duration_ms: int
    text: str
    format: str = "lpcm"
    sample_rate: int = 8000


class YandexTTSService:
    """Сервис синтеза речи через Yandex SpeechKit.

    Usage:
        tts = YandexTTSService(api_key="...", folder_id="...")
        result = await tts.synthesize("Здравствуйте, чем могу помочь?")
        # result.audio_data -> bytes (LINEAR16, 8kHz)
    """

    def __init__(
        self,
        *,
        api_key: str,
        folder_id: str,
        voice: str = "alena",
        speed: float = 1.0,
        emotion: str = "neutral",
        sample_rate: int = 8000,
    ) -> None:
        self._api_key = api_key
        self._folder_id = folder_id
        self._voice = voice
        self._speed = speed
        self._emotion = emotion
        self._sample_rate = sample_rate

    async def synthesize(self, text: str, *, ssml: bool = False) -> TTSResult:
        """Синтезирует речь из текста.

        Args:
            text: Текст для синтеза (или SSML-разметка).
            ssml: Если True, text интерпретируется как SSML.

        Returns:
            TTSResult с audio_data (LINEAR16 PCM).
        """
        logger.info("TTS: синтез текста (%d символов)", len(text))

        form_data = {
            "folderId": self._folder_id,
            "voice": self._voice,
            "speed": str(self._speed),
            "emotion": self._emotion,
            "format": "lpcm",
            "sampleRateHertz": str(self._sample_rate),
        }

        if ssml:
            form_data["ssml"] = text
        else:
            form_data["text"] = text

        headers = {"Authorization": f"Api-Key {self._api_key}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                TTS_API_URL,
                data=form_data,
                headers=headers,
            )
            response.raise_for_status()
            audio_data = response.content

        # Длительность: bytes / (sample_rate * 2 bytes per sample) * 1000 ms
        duration_ms = int(len(audio_data) / (self._sample_rate * 2) * 1000)

        logger.info(
            "TTS: синтезировано %d байт аудио (~%d мс)",
            len(audio_data),
            duration_ms,
        )

        return TTSResult(
            audio_data=audio_data,
            duration_ms=duration_ms,
            text=text,
            format="lpcm",
            sample_rate=self._sample_rate,
        )

    async def synthesize_ssml(self, ssml_text: str) -> TTSResult:
        """Синтезирует речь из SSML-разметки."""
        return await self.synthesize(ssml_text, ssml=True)

    def build_greeting_ssml(self, client_name: str | None = None) -> str:
        """Собирает SSML для приветствия."""
        if client_name:
            return (
                '<speak>'
                f'Здравствуйте, {client_name}.'
                '<break time="300ms"/>'
                'Вы позвонили в компанию франчайзи 1С.'
                '<break time="200ms"/>'
                'Чем могу помочь?'
                '</speak>'
            )
        return (
            '<speak>'
            'Здравствуйте!'
            '<break time="300ms"/>'
            'Вы позвонили в компанию франчайзи 1С.'
            '<break time="200ms"/>'
            'Представьтесь, пожалуйста, и расскажите, чем мы можем помочь.'
            '</speak>'
        )

    def build_farewell_ssml(self, task_number: str | None = None) -> str:
        """Собирает SSML для прощания."""
        if task_number:
            return (
                '<speak>'
                f'Ваше обращение зарегистрировано под номером {task_number}.'
                '<break time="300ms"/>'
                'Специалист свяжется с вами в ближайшее время.'
                '<break time="200ms"/>'
                'Спасибо за звонок! До свидания.'
                '</speak>'
            )
        return (
            '<speak>'
            'Спасибо за звонок!'
            '<break time="200ms"/>'
            'До свидания.'
            '</speak>'
        )
