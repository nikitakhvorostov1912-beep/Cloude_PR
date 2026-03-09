"""Тесты оркестратора диалога (интеграция STT → Claude → TTS)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from core.state_machine import DialogState
from models.task import ClientInfo
from services.ai_agent import AgentAction, AgentResponse, AIAgent, DialogContext
from services.dialog_orchestrator import DialogOrchestrator, DialogSession
from services.stt import STTResult, YandexSTTService
from services.tts import TTSResult, YandexTTSService


@pytest.fixture
def mock_stt():
    stt = MagicMock(spec=YandexSTTService)
    mock_session = MagicMock()
    mock_session.feed_audio = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.stats = MagicMock(chunks_received=0, bytes_received=0, results_emitted=0)
    # Пустая очередь
    import asyncio
    mock_session._results_queue = asyncio.Queue()
    stt.create_session.return_value = mock_session
    return stt


@pytest.fixture
def mock_tts():
    tts = MagicMock(spec=YandexTTSService)
    tts.synthesize = AsyncMock(
        return_value=TTSResult(
            audio_data=b"\x00" * 8000,
            duration_ms=500,
            text="Ответ",
        )
    )
    tts.synthesize_ssml = AsyncMock(
        return_value=TTSResult(
            audio_data=b"\x00" * 16000,
            duration_ms=1000,
            text="Приветствие",
        )
    )
    tts.build_greeting_ssml.return_value = "<speak>Здравствуйте</speak>"
    tts.build_farewell_ssml.return_value = "<speak>До свидания</speak>"
    return tts


@pytest.fixture
def mock_ai():
    ai = MagicMock(spec=AIAgent)
    ai.create_context.return_value = DialogContext(
        call_id="call-001", client_info={}, max_questions=5
    )
    ai.process_input = AsyncMock(
        return_value=AgentResponse(
            action=AgentAction.RESPOND,
            text="Расскажите подробнее",
            latency_ms=150,
        )
    )
    return ai


@pytest.fixture
def mock_onec():
    from integrations.client_1c import OneCClient
    onec = MagicMock(spec=OneCClient)
    onec.create_task = AsyncMock()
    return onec


@pytest.fixture
def orchestrator(mock_stt, mock_tts, mock_ai, mock_onec):
    return DialogOrchestrator(
        stt=mock_stt,
        tts=mock_tts,
        ai_agent=mock_ai,
        onec_client=mock_onec,
    )


@pytest.fixture
def client_info():
    return ClientInfo(
        id="001",
        name="ООО Ромашка",
        product="КА",
        contract_status="active",
        assigned_specialist="Иванов Иван",
    )


# --- Начало диалога ---


class TestStartDialog:
    @pytest.mark.asyncio
    async def test_start_returns_greeting(self, orchestrator, client_info):
        """start_dialog возвращает TTS приветствие."""
        result = await orchestrator.start_dialog(
            "call-001", "+79001234567", client_info
        )

        assert isinstance(result, TTSResult)
        assert len(result.audio_data) > 0

    @pytest.mark.asyncio
    async def test_start_creates_session(self, orchestrator, client_info):
        """start_dialog создаёт сессию."""
        await orchestrator.start_dialog("call-001", "+79001234567", client_info)

        session = orchestrator.get_session("call-001")
        assert session is not None
        assert session.call_id == "call-001"
        assert session.caller_number == "+79001234567"
        assert session.client_info == client_info

    @pytest.mark.asyncio
    async def test_start_initializes_fsm(self, orchestrator):
        """start_dialog инициализирует FSM в LISTENING."""
        await orchestrator.start_dialog("call-001", "+79001234567")

        session = orchestrator.get_session("call-001")
        assert session.fsm is not None
        assert session.fsm.state == DialogState.LISTENING

    @pytest.mark.asyncio
    async def test_start_unknown_client(self, orchestrator):
        """start_dialog без client_info."""
        result = await orchestrator.start_dialog("call-002", "+79009999999")
        assert isinstance(result, TTSResult)

    @pytest.mark.asyncio
    async def test_active_sessions_count(self, orchestrator):
        """Подсчёт активных сессий."""
        assert orchestrator.active_sessions_count == 0
        await orchestrator.start_dialog("call-001", "+79001234567")
        assert orchestrator.active_sessions_count == 1
        await orchestrator.start_dialog("call-002", "+79002222222")
        assert orchestrator.active_sessions_count == 2


# --- Обработка аудио ---


class TestHandleAudioChunk:
    @pytest.mark.asyncio
    async def test_handle_unknown_call(self, orchestrator):
        """Аудио для неизвестного call_id -> None."""
        result = await orchestrator.handle_audio_chunk("unknown", b"\x00" * 320)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_audio_feeds_stt(self, orchestrator, mock_stt):
        """handle_audio_chunk отправляет данные в STT."""
        await orchestrator.start_dialog("call-001", "+79001234567")
        await orchestrator.handle_audio_chunk("call-001", b"\x00" * 320)

        session = orchestrator.get_session("call-001")
        assert session.stt_session.feed_audio.called

    @pytest.mark.asyncio
    async def test_handle_audio_records_input(self, orchestrator):
        """handle_audio_chunk записывает входящее аудио."""
        await orchestrator.start_dialog("call-001", "+79001234567")
        await orchestrator.handle_audio_chunk("call-001", b"\x01\x02" * 160)

        session = orchestrator.get_session("call-001")
        assert len(session.recorder._input_buffer) > 0


# --- Завершение диалога ---


class TestEndDialog:
    @pytest.mark.asyncio
    async def test_end_returns_result(self, orchestrator):
        """end_dialog возвращает результат."""
        await orchestrator.start_dialog("call-001", "+79001234567")
        result = await orchestrator.end_dialog("call-001")

        assert result is not None
        assert result["call_id"] == "call-001"
        assert "duration_seconds" in result

    @pytest.mark.asyncio
    async def test_end_removes_session(self, orchestrator):
        """end_dialog удаляет сессию."""
        await orchestrator.start_dialog("call-001", "+79001234567")
        await orchestrator.end_dialog("call-001")

        assert orchestrator.get_session("call-001") is None

    @pytest.mark.asyncio
    async def test_end_unknown_call(self, orchestrator):
        """end_dialog для неизвестного call_id -> None."""
        result = await orchestrator.end_dialog("unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_end_closes_stt(self, orchestrator, mock_stt):
        """end_dialog закрывает STT сессию."""
        await orchestrator.start_dialog("call-001", "+79001234567")
        await orchestrator.end_dialog("call-001")

        mock_stt.create_session.return_value.close.assert_called_once()
