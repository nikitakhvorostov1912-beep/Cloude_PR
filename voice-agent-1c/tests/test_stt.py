"""Тесты STT сервиса (Yandex SpeechKit)."""
from __future__ import annotations

import asyncio
import struct

import pytest
import pytest_asyncio

from services.stt import (
    SILENCE_RMS_THRESHOLD,
    STTResult,
    STTSession,
    YandexSTTService,
)


@pytest.fixture
def stt_service():
    return YandexSTTService(
        api_key="test_key",
        folder_id="test_folder",
        silence_threshold_ms=200,  # Короткий порог для тестов
    )


@pytest.fixture
def stt_session(stt_service):
    return stt_service.create_session()


# --- VAD тесты ---


class TestVAD:
    def test_detect_silence(self, stt_session):
        """Тишина (нули) -> False."""
        silence = struct.pack("<160h", *([0] * 160))
        assert stt_session._detect_speech(silence) is False

    def test_detect_speech(self, stt_session):
        """Громкий сигнал -> True."""
        loud = struct.pack("<160h", *([5000] * 160))
        assert stt_session._detect_speech(loud) is True

    def test_detect_low_noise(self, stt_session):
        """Низкий шум ниже порога -> False."""
        low_noise = struct.pack("<160h", *([100] * 160))
        assert stt_session._detect_speech(low_noise) is False

    def test_detect_speech_threshold(self, stt_session):
        """Сигнал на границе порога."""
        # Чуть выше порога
        level = SILENCE_RMS_THRESHOLD + 50
        signal = struct.pack("<160h", *([level] * 160))
        assert stt_session._detect_speech(signal) is True

    def test_empty_chunk(self, stt_session):
        """Пустой чанк -> False."""
        assert stt_session._detect_speech(b"") is False

    def test_single_byte(self, stt_session):
        """Один байт -> False (недостаточно для сэмпла)."""
        assert stt_session._detect_speech(b"\x00") is False


# --- STT Session тесты ---


class TestSTTSession:
    @pytest.mark.asyncio
    async def test_session_creation(self, stt_service):
        """Сессия создаётся с правильными параметрами."""
        session = stt_service.create_session()
        assert session._sample_rate == 8000
        assert session._language == "ru-RU"
        assert session.stats.chunks_received == 0

    @pytest.mark.asyncio
    async def test_feed_audio_updates_stats(self, stt_session):
        """feed_audio обновляет статистику."""
        chunk = b"\x00" * 320
        await stt_session.feed_audio(chunk)
        assert stt_session.stats.chunks_received == 1
        assert stt_session.stats.bytes_received == 320

    @pytest.mark.asyncio
    async def test_feed_audio_multiple_chunks(self, stt_session):
        """Несколько чанков увеличивают счётчик."""
        for _ in range(5):
            await stt_session.feed_audio(b"\x00" * 320)
        assert stt_session.stats.chunks_received == 5
        assert stt_session.stats.bytes_received == 1600

    @pytest.mark.asyncio
    async def test_closed_session_ignores_audio(self, stt_session):
        """Закрытая сессия игнорирует аудио."""
        await stt_session.close()
        await stt_session.feed_audio(b"\x00" * 320)
        assert stt_session.stats.chunks_received == 0

    @pytest.mark.asyncio
    async def test_close_session(self, stt_session):
        """Закрытие сессии ставит None в очередь."""
        await stt_session.close()
        assert stt_session._closed is True
        result = await stt_session._results_queue.get()
        assert result is None

    @pytest.mark.asyncio
    async def test_force_finalize_empty(self, stt_session):
        """force_finalize с пустым буфером -> None."""
        result = await stt_session.force_finalize()
        assert result is None


# --- STT Result тесты ---


class TestSTTResult:
    def test_result_defaults(self):
        """STTResult с дефолтами."""
        result = STTResult(text="привет")
        assert result.text == "привет"
        assert result.confidence == 1.0
        assert result.is_final is False
        assert result.end_of_utterance is False

    def test_result_final(self):
        """STTResult финальный."""
        result = STTResult(
            text="Не проводятся документы",
            confidence=0.95,
            is_final=True,
            end_of_utterance=True,
        )
        assert result.is_final is True
        assert result.confidence == 0.95


# --- REST API тесты ---


class TestSTTRestAPI:
    @pytest.mark.asyncio
    async def test_recognize_short(self, stt_service, httpx_mock):
        """REST API распознавание короткого аудио."""
        httpx_mock.add_response(
            method="POST",
            json={"result": "Здравствуйте"},
        )

        result = await stt_service.recognize_short(b"\x00" * 16000)
        assert result.text == "Здравствуйте"
        assert result.is_final is True
        assert result.end_of_utterance is True
