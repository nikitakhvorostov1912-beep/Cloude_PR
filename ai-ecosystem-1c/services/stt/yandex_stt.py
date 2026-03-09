"""Yandex SpeechKit STT service — REST API with VAD integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

import httpx

from orchestrator.config import YandexSettings
from services.stt.buffer import AudioBuffer
from services.stt.vad import VoiceActivityDetector

logger = logging.getLogger(__name__)

YANDEX_STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


@dataclass(frozen=True)
class STTResult:
    text: str
    confidence: float = 1.0
    is_final: bool = False
    end_of_utterance: bool = False


@dataclass
class STTSessionStats:
    chunks_received: int = 0
    bytes_received: int = 0
    results_emitted: int = 0
    started_at: float = field(default_factory=lambda: __import__("time").monotonic())


class STTSession:
    """Manages a single STT recognition session with VAD."""

    def __init__(self, settings: YandexSettings) -> None:
        self._settings = settings
        self._vad = VoiceActivityDetector(
            silence_threshold_ms=settings.stt_silence_threshold_ms,
            sample_rate=settings.stt_sample_rate,
        )
        self._buffer = AudioBuffer(chunk_size=settings.stt_sample_rate * 2)  # 1 sec
        self._results: asyncio.Queue[Optional[STTResult]] = asyncio.Queue()
        self._closed = False
        self._stats = STTSessionStats()

    async def feed_audio(self, data: bytes) -> None:
        """Feed raw PCM audio data to the session."""
        if self._closed:
            return
        self._stats.chunks_received += 1
        self._stats.bytes_received += len(data)
        self._vad.feed(data)

        chunks = self._buffer.append(data)
        for chunk in chunks:
            if self._vad.is_silent:
                continue
            result = await self._recognize_chunk(chunk)
            if result:
                self._stats.results_emitted += 1
                await self._results.put(result)

        if self._vad.is_silent and self._buffer.pending_bytes > 0:
            remaining = self._buffer.flush()
            if remaining and len(remaining) > 1600:  # at least 100ms of audio
                result = await self._recognize_chunk(remaining)
                if result:
                    self._stats.results_emitted += 1
                    await self._results.put(
                        STTResult(
                            text=result.text,
                            confidence=result.confidence,
                            is_final=True,
                            end_of_utterance=True,
                        )
                    )

    async def force_finalize(self) -> Optional[STTResult]:
        """Process any remaining audio in the buffer."""
        remaining = self._buffer.flush()
        if remaining and len(remaining) > 1600:
            return await self._recognize_chunk(remaining)
        return None

    async def listen_results(self) -> AsyncGenerator[STTResult, None]:
        """Async generator yielding STT results as they arrive."""
        while not self._closed:
            try:
                result = await asyncio.wait_for(self._results.get(), timeout=0.5)
                if result is None:
                    break
                yield result
            except asyncio.TimeoutError:
                continue

    async def close(self) -> None:
        self._closed = True
        await self._results.put(None)

    @property
    def stats(self) -> STTSessionStats:
        return self._stats

    async def _recognize_chunk(self, audio_data: bytes) -> Optional[STTResult]:
        """Send audio to Yandex STT REST API."""
        if not self._settings.api_key:
            logger.debug("STT: no API key, skipping recognition")
            return None
        try:
            params = {
                "folderId": self._settings.folder_id,
                "lang": self._settings.stt_language,
                "format": "lpcm",
                "sampleRateHertz": str(self._settings.stt_sample_rate),
            }
            headers = {"Authorization": f"Api-Key {self._settings.api_key}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    YANDEX_STT_URL,
                    params=params,
                    headers=headers,
                    content=audio_data,
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("result", "")
                if text:
                    return STTResult(text=text, confidence=0.9, is_final=True)
        except Exception:
            logger.exception("STT recognition failed")
        return None


class YandexSTTService:
    """Factory for STT sessions."""

    def __init__(self, settings: YandexSettings) -> None:
        self._settings = settings

    def create_session(self) -> STTSession:
        return STTSession(self._settings)
