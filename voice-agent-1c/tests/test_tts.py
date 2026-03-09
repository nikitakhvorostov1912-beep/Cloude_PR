"""Тесты TTS сервиса (Yandex SpeechKit)."""
from __future__ import annotations

import pytest

from services.tts import TTS_API_URL, TTSResult, YandexTTSService


@pytest.fixture
def tts_service():
    return YandexTTSService(
        api_key="test_key",
        folder_id="test_folder",
        voice="alena",
        speed=1.0,
        emotion="neutral",
        sample_rate=8000,
    )


# --- Синтез ---


class TestTTSSynthesize:
    @pytest.mark.asyncio
    async def test_synthesize_text(self, tts_service, httpx_mock):
        """Синтез текста -> аудио."""
        # 1 секунда аудио (8000 samples * 2 bytes = 16000 bytes)
        fake_audio = b"\x00" * 16000
        httpx_mock.add_response(
            url=TTS_API_URL,
            content=fake_audio,
        )

        result = await tts_service.synthesize("Здравствуйте")
        assert isinstance(result, TTSResult)
        assert len(result.audio_data) == 16000
        assert result.duration_ms == 1000  # 16000 / (8000 * 2) * 1000
        assert result.text == "Здравствуйте"
        assert result.format == "lpcm"
        assert result.sample_rate == 8000

    @pytest.mark.asyncio
    async def test_synthesize_ssml(self, tts_service, httpx_mock):
        """Синтез SSML -> аудио."""
        fake_audio = b"\x00" * 32000
        httpx_mock.add_response(url=TTS_API_URL, content=fake_audio)

        ssml = '<speak>Здравствуйте<break time="300ms"/>Чем могу помочь?</speak>'
        result = await tts_service.synthesize(ssml, ssml=True)
        assert len(result.audio_data) == 32000
        assert result.duration_ms == 2000

    @pytest.mark.asyncio
    async def test_synthesize_ssml_method(self, tts_service, httpx_mock):
        """synthesize_ssml вызывает synthesize(ssml=True)."""
        fake_audio = b"\x00" * 8000
        httpx_mock.add_response(url=TTS_API_URL, content=fake_audio)

        result = await tts_service.synthesize_ssml("<speak>Тест</speak>")
        assert isinstance(result, TTSResult)

    @pytest.mark.asyncio
    async def test_synthesize_request_params(self, tts_service, httpx_mock):
        """Проверка параметров запроса к TTS API."""
        httpx_mock.add_response(url=TTS_API_URL, content=b"\x00" * 100)

        await tts_service.synthesize("Тест")

        request = httpx_mock.get_request()
        assert request is not None
        assert "Api-Key test_key" in request.headers.get("authorization", "")

    @pytest.mark.asyncio
    async def test_empty_text(self, tts_service, httpx_mock):
        """Пустой текст -> пустое аудио."""
        httpx_mock.add_response(url=TTS_API_URL, content=b"")

        result = await tts_service.synthesize("")
        assert len(result.audio_data) == 0
        assert result.duration_ms == 0


# --- SSML-шаблоны ---


class TestTTSTemplates:
    def test_greeting_known_client(self, tts_service):
        """Приветствие для известного клиента."""
        ssml = tts_service.build_greeting_ssml("ООО Ромашка")
        assert "ООО Ромашка" in ssml
        assert "<speak>" in ssml
        assert "<break" in ssml

    def test_greeting_unknown_client(self, tts_service):
        """Приветствие для нового клиента."""
        ssml = tts_service.build_greeting_ssml()
        assert "Здравствуйте!" in ssml
        assert "Представьтесь" in ssml

    def test_greeting_none_client(self, tts_service):
        """Приветствие без имени клиента."""
        ssml = tts_service.build_greeting_ssml(None)
        assert "Представьтесь" in ssml

    def test_farewell_with_task(self, tts_service):
        """Прощание с номером задачи."""
        ssml = tts_service.build_farewell_ssml("4521")
        assert "4521" in ssml
        assert "Спасибо за звонок" in ssml

    def test_farewell_without_task(self, tts_service):
        """Прощание без номера задачи."""
        ssml = tts_service.build_farewell_ssml()
        assert "Спасибо за звонок" in ssml
        assert "До свидания" in ssml


# --- TTSResult ---


class TestTTSResult:
    def test_result_creation(self):
        """Создание TTSResult."""
        result = TTSResult(
            audio_data=b"\x00" * 100,
            duration_ms=500,
            text="Тест",
        )
        assert result.audio_data == b"\x00" * 100
        assert result.duration_ms == 500
        assert result.format == "lpcm"
        assert result.sample_rate == 8000
