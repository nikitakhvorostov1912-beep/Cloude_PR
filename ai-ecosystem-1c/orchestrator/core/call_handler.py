"""Main call pipeline — orchestrates the full call lifecycle.

Incoming call → dedup check → client lookup → STT → classification →
task creation → notifications → cleanup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from models.api.call import CallResult, MangoCallEvent
from models.api.client import ClientContext
from models.api.task import ClassificationResult, TaskResponse
from orchestrator.core.call_session import CallSessionStore
from orchestrator.core.deduplication import DeduplicationService
from orchestrator.core.routing_engine import RoutingEngine

logger = logging.getLogger(__name__)


@dataclass
class CallPipelineResult:
    """Result of processing an incoming call."""

    call_id: str
    phone: str
    client: Optional[ClientContext] = None
    classification: Optional[ClassificationResult] = None
    task: Optional[TaskResponse] = None
    escalated: bool = False
    deduplicated: bool = False
    warnings: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


class CallHandler:
    """Orchestrates the full call processing pipeline.

    Dependencies are injected at construction time.
    """

    def __init__(
        self,
        *,
        session_store: CallSessionStore,
        dedup: DeduplicationService,
        routing: RoutingEngine,
        client_resolver: Any = None,
        task_creator: Any = None,
        notifier: Any = None,
    ) -> None:
        self._sessions = session_store
        self._dedup = dedup
        self._routing = routing
        self._client_resolver = client_resolver
        self._task_creator = task_creator
        self._notifier = notifier

    async def handle_incoming(
        self,
        event: MangoCallEvent,
    ) -> CallPipelineResult:
        """Process an incoming call event through the pipeline."""
        call_id = event.call_id
        phone = event.from_number

        logger.info("call_id=%s phone=%s pipeline_start", call_id, phone)

        result = CallPipelineResult(call_id=call_id, phone=phone)

        # 1. Deduplication check
        existing = await self._dedup.check(phone)
        if existing is not None:
            logger.info(
                "call_id=%s dedup_hit previous_call=%s task=%s",
                call_id,
                existing.call_id,
                existing.task_number,
            )
            result.deduplicated = True
            result.warnings.append(
                f"Повторный звонок. Предыдущая задача: {existing.task_number or 'N/A'}"
            )

        # 2. Initialize session
        await self._sessions.set(
            call_id,
            {
                "phone": phone,
                "status": "active",
                "deduplicated": result.deduplicated,
            },
        )

        # 3. Resolve client (if resolver available)
        if self._client_resolver is not None:
            try:
                client = await self._client_resolver(phone)
                result.client = client
                await self._sessions.update(
                    call_id,
                    client_name=client.name if client and client.found else None,
                )
            except Exception:
                logger.exception("call_id=%s client resolution failed", call_id)

        return result

    async def handle_classification(
        self,
        *,
        call_id: str,
        transcript: str,
        client_context: Optional[str] = None,
    ) -> CallPipelineResult:
        """Classify a completed call and create a task if needed."""
        session_data = await self._sessions.get(call_id)
        phone = session_data.get("phone", "") if session_data else ""

        result = CallPipelineResult(call_id=call_id, phone=phone)

        # 1. Route through classifier
        decision = await self._routing.route(
            call_id=call_id,
            transcript=transcript,
            client_context=client_context,
        )
        result.classification = decision.classification
        result.warnings.extend(decision.warnings)

        if decision.needs_escalation:
            result.escalated = True
            logger.info("call_id=%s escalated", call_id)
            await self._sessions.update(call_id, status="escalated")
            return result

        # 2. Create task (if creator available)
        if decision.should_create_task and self._task_creator is not None:
            try:
                task = await self._task_creator(
                    call_id=call_id,
                    classification=decision.classification,
                    phone=phone,
                )
                result.task = task

                # Register for deduplication
                await self._dedup.register(
                    phone=phone,
                    call_id=call_id,
                    task_number=task.task_number if task else None,
                    department=decision.classification.department.value,
                )
            except Exception:
                logger.exception("call_id=%s task creation failed", call_id)
                result.warnings.append("Ошибка создания задачи")

        # 3. Update session
        await self._sessions.update(call_id, status="classified")

        return result

    async def handle_hangup(self, call_id: str) -> None:
        """Clean up after call ends."""
        logger.info("call_id=%s hangup", call_id)
        await self._sessions.update(call_id, status="completed")
