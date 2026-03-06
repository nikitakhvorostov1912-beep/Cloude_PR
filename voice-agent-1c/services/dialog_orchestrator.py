"""Центральный оркестратор диалога: Audio -> STT -> Claude -> TTS -> Audio.

Управляет полным жизненным циклом голосового диалога:
1. Принимает аудио от Mango Office (WebSocket)
2. Отправляет на STT (Yandex SpeechKit)
3. Передаёт распознанный текст Claude AI Agent
4. Синтезирует ответ через TTS (Yandex SpeechKit)
5. Отправляет аудио обратно
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from core.state_machine import DialogEvent, DialogState, DialogStateMachine
from integrations.client_1c import OneCClient, OneCError
from models.task import ClientInfo, TaskCreate
from services.ai_agent import AgentAction, AgentResponse, AIAgent, DialogContext
from services.audio_recorder import AudioRecorder
from services.stt import STTResult, STTSession, YandexSTTService
from services.tts import TTSResult, YandexTTSService

logger = logging.getLogger(__name__)


@dataclass
class DialogSession:
    """Активная сессия диалога."""

    call_id: str
    caller_number: str
    client_info: ClientInfo | None = None
    fsm: DialogStateMachine | None = None
    ai_context: DialogContext | None = None
    stt_session: STTSession | None = None
    recorder: AudioRecorder | None = None
    started_at: float = field(default_factory=time.time)
    task_id: str | None = None


class DialogOrchestrator:
    """Оркестратор голосового диалога.

    Usage:
        orchestrator = DialogOrchestrator(stt=..., tts=..., ai=..., onec=...)
        session = await orchestrator.start_dialog("call-001", "+79001234567")
        # В цикле WebSocket:
        audio_response = await orchestrator.handle_audio_chunk("call-001", chunk)
        if audio_response:
            ws.send_bytes(audio_response)
    """

    def __init__(
        self,
        *,
        stt: YandexSTTService,
        tts: YandexTTSService,
        ai_agent: AIAgent,
        onec_client: OneCClient,
    ) -> None:
        self._stt = stt
        self._tts = tts
        self._ai = ai_agent
        self._onec = onec_client
        self._sessions: dict[str, DialogSession] = {}

    async def start_dialog(
        self,
        call_id: str,
        caller_number: str,
        client_info: ClientInfo | None = None,
    ) -> TTSResult:
        """Начинает новый диалог.

        1. Создаёт FSM, STT-сессию, AI-контекст
        2. Генерирует приветствие через TTS
        3. Возвращает аудио приветствия

        Returns:
            TTSResult с аудио приветствия.
        """
        logger.info("Начало диалога: call_id=%s, phone=%s", call_id, caller_number)

        # Подготовка клиентских данных для AI
        client_dict: dict = {}
        if client_info:
            client_dict = {
                "found": True,
                "name": client_info.name,
                "product": client_info.product,
                "assigned_specialist": client_info.assigned_specialist,
            }

        # Создание компонентов сессии
        fsm = DialogStateMachine(call_id)
        fsm.transition(DialogEvent.INCOMING_CALL)  # IDLE -> GREETING

        stt_session = self._stt.create_session()
        ai_context = self._ai.create_context(
            call_id=call_id, client_info=client_dict
        )
        recorder = AudioRecorder(call_id)

        session = DialogSession(
            call_id=call_id,
            caller_number=caller_number,
            client_info=client_info,
            fsm=fsm,
            ai_context=ai_context,
            stt_session=stt_session,
            recorder=recorder,
        )
        self._sessions[call_id] = session

        # Синтез приветствия
        client_name = client_info.name if client_info else None
        greeting_ssml = self._tts.build_greeting_ssml(client_name)
        greeting_audio = await self._tts.synthesize_ssml(greeting_ssml)

        # Записываем аудио ответа
        recorder.feed_output(greeting_audio.audio_data)

        # GREETING -> LISTENING
        fsm.transition(DialogEvent.GREETING_PLAYED)

        logger.info(
            "Диалог начат: call_id=%s, greeting=%d bytes",
            call_id,
            len(greeting_audio.audio_data),
        )

        return greeting_audio

    async def handle_audio_chunk(
        self, call_id: str, chunk: bytes
    ) -> TTSResult | None:
        """Обрабатывает аудио чанк от клиента.

        1. Записывает аудио
        2. Отправляет в STT
        3. Если STT вернул результат — обрабатывает через AI
        4. Если AI ответил — синтезирует TTS

        Returns:
            TTSResult если есть ответ, None если нет.
        """
        session = self._sessions.get(call_id)
        if not session or not session.stt_session:
            return None

        # Записываем входящее аудио
        if session.recorder:
            session.recorder.feed_input(chunk)

        # Отправляем в STT
        await session.stt_session.feed_audio(chunk)

        # Проверяем результаты STT (неблокирующе)
        try:
            result = session.stt_session._results_queue.get_nowait()
            if result and result.text.strip():
                return await self._process_stt_result(session, result)
        except asyncio.QueueEmpty:
            pass

        return None

    async def _process_stt_result(
        self, session: DialogSession, stt_result: STTResult
    ) -> TTSResult | None:
        """Обрабатывает результат распознавания речи."""
        fsm = session.fsm
        if not fsm or not session.ai_context:
            return None

        logger.info(
            "STT результат [%s]: '%s' (confidence=%.2f)",
            session.call_id,
            stt_result.text,
            stt_result.confidence,
        )

        # LISTENING -> PROCESSING
        if fsm.can_transition(DialogEvent.SPEECH_RECOGNIZED):
            fsm.transition(DialogEvent.SPEECH_RECOGNIZED)

        # Обрабатываем через AI
        ai_response = await self._ai.process_input(
            stt_result.text,
            session.ai_context,
            stt_confidence=stt_result.confidence,
        )

        logger.info(
            "AI ответ [%s]: action=%s, latency=%dms",
            session.call_id,
            ai_response.action,
            ai_response.latency_ms,
        )

        # Обрабатываем действие AI
        return await self._handle_ai_response(session, ai_response)

    async def _handle_ai_response(
        self, session: DialogSession, response: AgentResponse
    ) -> TTSResult | None:
        """Обрабатывает ответ AI-агента и синтезирует аудио."""
        fsm = session.fsm
        if not fsm:
            return None

        if response.action == AgentAction.CREATE_TASK:
            return await self._handle_create_task(session, response)
        elif response.action == AgentAction.ESCALATE:
            return await self._handle_escalation(session, response)
        else:
            # RESPOND / CLARIFY — обычный ответ
            return await self._handle_respond(session, response)

    async def _handle_respond(
        self, session: DialogSession, response: AgentResponse
    ) -> TTSResult:
        """Озвучивает ответ агента."""
        fsm = session.fsm
        if fsm and fsm.can_transition(DialogEvent.AI_RESPOND):
            fsm.transition(DialogEvent.AI_RESPOND)  # PROCESSING -> RESPONDING

        audio = await self._tts.synthesize(response.text)

        if session.recorder:
            session.recorder.feed_output(audio.audio_data)

        if fsm and fsm.can_transition(DialogEvent.RESPONSE_PLAYED):
            fsm.transition(DialogEvent.RESPONSE_PLAYED)  # RESPONDING -> LISTENING

        return audio

    async def _handle_create_task(
        self, session: DialogSession, response: AgentResponse
    ) -> TTSResult:
        """Создаёт задачу в 1С и озвучивает подтверждение."""
        fsm = session.fsm
        if fsm and fsm.can_transition(DialogEvent.AI_CREATE_TASK):
            fsm.transition(DialogEvent.AI_CREATE_TASK)  # PROCESSING -> TASK_CREATING

        task_number = None

        if response.classification:
            try:
                task_data = TaskCreate(
                    client_id=(
                        session.client_info.id if session.client_info else None
                    ),
                    department=response.classification.department,
                    product=response.classification.product,
                    task_type=response.classification.task_type,
                    priority=response.classification.priority,
                    summary=response.classification.summary,
                    description=response.classification.description,
                    call_id=session.call_id,
                )
                task_response = await self._onec.create_task(task_data)
                session.task_id = task_response.task_id
                task_number = task_response.task_number

                if fsm and fsm.can_transition(DialogEvent.TASK_CREATED):
                    fsm.transition(DialogEvent.TASK_CREATED)

                logger.info(
                    "Задача создана [%s]: task_id=%s",
                    session.call_id,
                    task_response.task_id,
                )
            except OneCError:
                logger.exception("Ошибка создания задачи в 1С [%s]", session.call_id)
                if fsm and fsm.can_transition(DialogEvent.ERROR_OCCURRED):
                    fsm.transition(DialogEvent.ERROR_OCCURRED)

        # Синтез прощания
        farewell_ssml = self._tts.build_farewell_ssml(task_number)
        audio = await self._tts.synthesize_ssml(farewell_ssml)

        if session.recorder:
            session.recorder.feed_output(audio.audio_data)

        # Автоподтверждение -> прощание -> завершение
        if fsm and fsm.can_transition(DialogEvent.CLIENT_CONFIRMED):
            fsm.transition(DialogEvent.CLIENT_CONFIRMED)
        if fsm and fsm.can_transition(DialogEvent.FAREWELL_PLAYED):
            fsm.transition(DialogEvent.FAREWELL_PLAYED)

        return audio

    async def _handle_escalation(
        self, session: DialogSession, response: AgentResponse
    ) -> TTSResult:
        """Эскалация — переводит на оператора."""
        fsm = session.fsm
        if fsm and fsm.can_transition(DialogEvent.AI_ESCALATE):
            fsm.transition(DialogEvent.AI_ESCALATE)

        audio = await self._tts.synthesize(response.text)

        if session.recorder:
            session.recorder.feed_output(audio.audio_data)

        logger.info(
            "Эскалация [%s]: reason=%s",
            session.call_id,
            response.escalation_reason,
        )

        return audio

    async def end_dialog(self, call_id: str) -> dict | None:
        """Завершает диалог и возвращает результат."""
        session = self._sessions.pop(call_id, None)
        if not session:
            return None

        # Закрываем STT
        if session.stt_session:
            await session.stt_session.close()

        # Завершаем FSM
        if session.fsm and session.fsm.can_transition(DialogEvent.CALL_ENDED):
            session.fsm.transition(DialogEvent.CALL_ENDED)

        # Финализируем запись
        transcript = None
        if session.recorder:
            transcript = await session.recorder.finalize()

        duration = int(time.time() - session.started_at)

        result = {
            "call_id": call_id,
            "caller_number": session.caller_number,
            "client_info": (
                session.client_info.model_dump() if session.client_info else None
            ),
            "task_id": session.task_id,
            "duration_seconds": duration,
            "fsm_history": session.fsm.to_dict() if session.fsm else None,
            "transcript": transcript,
        }

        logger.info(
            "Диалог завершён [%s]: duration=%ds, task_id=%s",
            call_id,
            duration,
            session.task_id,
        )

        return result

    def get_session(self, call_id: str) -> DialogSession | None:
        """Получает активную сессию."""
        return self._sessions.get(call_id)

    @property
    def active_sessions_count(self) -> int:
        return len(self._sessions)
