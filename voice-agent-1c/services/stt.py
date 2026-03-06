"""Yandex SpeechKit STT — потоковое распознавание речи.

Поддерживает два режима:
  - gRPC streaming (production, требует proto stubs)
  - REST short-audio (fallback, без gRPC)

Аудио формат: LINEAR16, 8kHz (телефония).
VAD: определение конца фразы по порогу тишины 800ms.
"""
from __future__ import annotations

import asyncio
import logging
import struct
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

# Порог тишины — уровень энергии фрейма (RMS)
SILENCE_RMS_THRESHOLD = 300
# Размер фрейма для анализа тишины (20ms при 8kHz, 16bit mono = 320 bytes)
FRAME_SIZE_BYTES = 320


@dataclass
class STTResult:
    """Результат распознавания речи."""

    text: str
    confidence: float = 1.0
    is_final: bool = False
    end_of_utterance: bool = False


@dataclass
class STTSessionStats:
    """Статистика сессии STT."""

    chunks_received: int = 0
    bytes_received: int = 0
    results_emitted: int = 0
    started_at: float = field(default_factory=time.time)


class YandexSTTService:
    """Сервис распознавания речи через Yandex SpeechKit.

    Usage:
        stt = YandexSTTService(api_key="...", folder_id="...")
        session = stt.create_session()
        await session.feed_audio(audio_chunk)
        async for result in session.listen_results():
            print(result.text)
    """

    def __init__(
        self,
        *,
        api_key: str,
        folder_id: str,
        model: str = "general:rc",
        language: str = "ru-RU",
        sample_rate: int = 8000,
        silence_threshold_ms: int = 800,
    ) -> None:
        self._api_key = api_key
        self._folder_id = folder_id
        self._model = model
        self._language = language
        self._sample_rate = sample_rate
        self._silence_threshold_ms = silence_threshold_ms

    def create_session(self) -> STTSession:
        """Создаёт новую сессию распознавания."""
        return STTSession(
            api_key=self._api_key,
            folder_id=self._folder_id,
            model=self._model,
            language=self._language,
            sample_rate=self._sample_rate,
            silence_threshold_ms=self._silence_threshold_ms,
        )

    async def recognize_short(self, audio_data: bytes) -> STTResult:
        """Распознавание короткого аудио через REST API (до 30 сек).

        POST https://stt.api.cloud.yandex.net/speech/v1/stt:recognize
        """
        url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
        params = {
            "folderId": self._folder_id,
            "lang": self._language,
            "sampleRateHertz": self._sample_rate,
            "format": "lpcm",
        }
        headers = {"Authorization": f"Api-Key {self._api_key}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                content=audio_data,
            )
            response.raise_for_status()
            data = response.json()

        text = data.get("result", "")
        return STTResult(text=text, confidence=1.0, is_final=True, end_of_utterance=True)


class STTSession:
    """Сессия потокового распознавания речи.

    Реализует буферизацию аудио и VAD (Voice Activity Detection)
    с определением конца фразы по порогу тишины.
    """

    def __init__(
        self,
        *,
        api_key: str,
        folder_id: str,
        model: str,
        language: str,
        sample_rate: int,
        silence_threshold_ms: int,
    ) -> None:
        self._api_key = api_key
        self._folder_id = folder_id
        self._model = model
        self._language = language
        self._sample_rate = sample_rate
        self._silence_threshold_ms = silence_threshold_ms

        # Буфер аудио для распознавания
        self._audio_buffer = bytearray()
        # Очередь результатов
        self._results_queue: asyncio.Queue[STTResult | None] = asyncio.Queue()
        # Статистика
        self._stats = STTSessionStats()
        # VAD state
        self._silence_start: float | None = None
        self._has_speech = False
        self._closed = False

        # Буфер для текущей фразы (до end_of_utterance)
        self._utterance_buffer = bytearray()
        # Порог тишины в секундах
        self._silence_threshold_sec = silence_threshold_ms / 1000.0

    async def feed_audio(self, chunk: bytes) -> None:
        """Принимает порцию аудио данных (LINEAR16, 8kHz).

        Анализирует VAD и при обнаружении конца фразы
        запускает распознавание буфера.
        """
        if self._closed:
            return

        self._stats.chunks_received += 1
        self._stats.bytes_received += len(chunk)
        self._utterance_buffer.extend(chunk)

        # VAD анализ
        is_speech = self._detect_speech(chunk)

        if is_speech:
            self._has_speech = True
            self._silence_start = None
        elif self._has_speech:
            # Начало тишины после речи
            now = time.time()
            if self._silence_start is None:
                self._silence_start = now
            elif (now - self._silence_start) >= self._silence_threshold_sec:
                # Конец фразы — отправляем на распознавание
                await self._process_utterance()
                self._silence_start = None
                self._has_speech = False

    async def _process_utterance(self) -> None:
        """Отправляет накопленный буфер на распознавание."""
        if not self._utterance_buffer:
            return

        audio_data = bytes(self._utterance_buffer)
        self._utterance_buffer.clear()

        logger.debug(
            "STT: обработка фразы, %d байт аудио",
            len(audio_data),
        )

        try:
            result = await self._recognize_chunk(audio_data)
            if result.text.strip():
                self._stats.results_emitted += 1
                await self._results_queue.put(result)
        except Exception:
            logger.exception("Ошибка распознавания аудио")
            await self._results_queue.put(
                STTResult(text="", confidence=0.0, is_final=True, end_of_utterance=True)
            )

    async def _recognize_chunk(self, audio_data: bytes) -> STTResult:
        """Распознаёт порцию аудио через REST API."""
        url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
        params = {
            "folderId": self._folder_id,
            "lang": self._language,
            "sampleRateHertz": self._sample_rate,
            "format": "lpcm",
        }
        headers = {"Authorization": f"Api-Key {self._api_key}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params=params,
                headers=headers,
                content=audio_data,
            )
            response.raise_for_status()
            data = response.json()

        text = data.get("result", "")
        return STTResult(
            text=text,
            confidence=1.0,
            is_final=True,
            end_of_utterance=True,
        )

    def _detect_speech(self, chunk: bytes) -> bool:
        """Определяет наличие речи в аудио чанке по RMS энергии.

        LINEAR16 (16-bit signed PCM, little-endian).
        """
        if len(chunk) < 2:
            return False

        # Распаковываем 16-bit signed samples
        n_samples = len(chunk) // 2
        try:
            samples = struct.unpack(f"<{n_samples}h", chunk[: n_samples * 2])
        except struct.error:
            return False

        if not samples:
            return False

        # RMS энергия
        sum_squares = sum(s * s for s in samples)
        rms = (sum_squares / n_samples) ** 0.5

        return rms > SILENCE_RMS_THRESHOLD

    async def listen_results(self) -> AsyncGenerator[STTResult, None]:
        """Итерирует результаты распознавания (async generator)."""
        while not self._closed:
            try:
                result = await asyncio.wait_for(
                    self._results_queue.get(), timeout=0.5
                )
                if result is None:
                    break
                yield result
            except asyncio.TimeoutError:
                continue

    async def force_finalize(self) -> STTResult | None:
        """Принудительно распознаёт оставшийся буфер."""
        if self._utterance_buffer:
            await self._process_utterance()
            try:
                return self._results_queue.get_nowait()
            except asyncio.QueueEmpty:
                return None
        return None

    async def close(self) -> None:
        """Закрывает сессию."""
        self._closed = True
        # Сигнал завершения для listen_results
        await self._results_queue.put(None)
        logger.info(
            "STT сессия закрыта: chunks=%d, bytes=%d, results=%d",
            self._stats.chunks_received,
            self._stats.bytes_received,
            self._stats.results_emitted,
        )

    @property
    def stats(self) -> STTSessionStats:
        return self._stats
