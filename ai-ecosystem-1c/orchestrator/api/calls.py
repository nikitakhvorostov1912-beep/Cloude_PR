"""WebSocket endpoint for real-time call streaming — WS /ws/call/{call_id}."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from orchestrator.dependencies import (
    get_call_handler,
    get_session_store,
    get_voice_agent,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["calls"])


class ConnectionManager:
    """Manages active WebSocket connections per call_id."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, call_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(call_id, []).append(ws)
        logger.info("ws connected: call_id=%s total=%d", call_id, len(self._connections[call_id]))

    def disconnect(self, call_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(call_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(call_id, None)

    async def broadcast(self, call_id: str, message: dict[str, Any]) -> None:
        """Send a JSON message to all connections for a call_id."""
        conns = self._connections.get(call_id, [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(call_id, ws)

    @property
    def active_connections(self) -> int:
        return sum(len(v) for v in self._connections.values())


manager = ConnectionManager()


@router.websocket("/ws/call/{call_id}")
async def call_websocket(
    ws: WebSocket,
    call_id: str,
) -> None:
    """WebSocket for real-time call updates.

    Client → Server messages:
        {"type": "audio", "data": "<base64 PCM>"}
        {"type": "text", "text": "user utterance"}

    Server → Client messages:
        {"type": "transcript", "speaker": "client"|"operator", "text": "..."}
        {"type": "classification", "data": {...}}
        {"type": "task_created", "task_number": "SAK-1234"}
        {"type": "state", "state": "listening"|"classifying"|...}
        {"type": "error", "message": "..."}
    """
    await manager.connect(call_id, ws)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "Неверный JSON"})
                continue

            msg_type = msg.get("type")

            if msg_type == "text":
                # Forward user text to dashboard observers
                await manager.broadcast(
                    call_id,
                    {
                        "type": "transcript",
                        "speaker": "client",
                        "text": msg.get("text", ""),
                    },
                )

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

            else:
                logger.debug("ws unknown msg type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("ws disconnected: call_id=%s", call_id)
    except Exception:
        logger.exception("ws error: call_id=%s", call_id)
    finally:
        manager.disconnect(call_id, ws)


@router.get("/api/calls/active")
async def get_active_calls(
    session_store: Any = Depends(get_session_store),
) -> dict[str, Any]:
    """Return count of active calls and WebSocket connections."""
    active = await session_store.get_active_count()
    return {
        "active_calls": active,
        "ws_connections": manager.active_connections,
    }
