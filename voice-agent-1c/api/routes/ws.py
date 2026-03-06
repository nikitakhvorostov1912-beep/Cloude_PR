"""WebSocket endpoint для аудио потока от Mango Office.

WS /ws/call/{call_id} — двунаправленный аудио поток:
  - Клиент -> Сервер: PCM аудио чанки (LINEAR16, 8kHz)
  - Сервер -> Клиент: PCM аудио ответы TTS
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.dialog_orchestrator import DialogOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/call/{call_id}")
async def websocket_call(websocket: WebSocket, call_id: str) -> None:
    """WebSocket endpoint для голосового диалога.

    Протокол:
    1. Клиент подключается и отправляет JSON с caller_number
    2. Сервер отправляет приветствие (bytes)
    3. Клиент отправляет аудио чанки (bytes)
    4. Сервер отправляет TTS ответы (bytes)
    5. При завершении — JSON с результатом
    """
    await websocket.accept()

    orchestrator: DialogOrchestrator | None = getattr(
        websocket.app.state, "dialog_orchestrator", None
    )
    if not orchestrator:
        await websocket.send_json({"error": "Оркестратор не инициализирован"})
        await websocket.close(code=1011)
        return

    logger.info("WS подключение: call_id=%s", call_id)

    try:
        # Получаем метаданные звонка
        init_data = await websocket.receive_json()
        caller_number = init_data.get("caller_number", "unknown")
        client_info_data = init_data.get("client_info")

        # Парсим client_info если передан
        client_info = None
        if client_info_data:
            from models.task import ClientInfo

            client_info = ClientInfo(**client_info_data)

        # Начинаем диалог
        greeting = await orchestrator.start_dialog(
            call_id, caller_number, client_info
        )

        # Отправляем приветствие
        await websocket.send_bytes(greeting.audio_data)

        # Основной цикл аудио
        while True:
            data = await websocket.receive_bytes()

            # Обрабатываем аудио чанк
            response = await orchestrator.handle_audio_chunk(call_id, data)

            if response:
                await websocket.send_bytes(response.audio_data)

                # Проверяем завершение диалога
                session = orchestrator.get_session(call_id)
                if session and session.fsm and session.fsm.is_terminal:
                    result = await orchestrator.end_dialog(call_id)
                    await websocket.send_json({"status": "completed", "result": result})
                    break

    except WebSocketDisconnect:
        logger.info("WS отключение: call_id=%s", call_id)
    except Exception:
        logger.exception("WS ошибка: call_id=%s", call_id)
    finally:
        # Завершаем диалог при любом исходе
        result = await orchestrator.end_dialog(call_id)
        if result:
            logger.info(
                "Диалог завершён после WS disconnect: call_id=%s, duration=%ds",
                call_id,
                result.get("duration_seconds", 0),
            )
