"""Call-related API models.

Covers Mango Office webhooks, in-flight call sessions (stored in Redis),
and the final call result returned after post-processing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CallEventType(StrEnum):
    INCOMING = "incoming"
    CONNECTED = "connected"
    COMPLETED = "completed"
    DISCONNECTED = "disconnected"


class MangoCallEvent(BaseModel):
    """Parsed payload from Mango Office webhook."""

    model_config = ConfigDict(frozen=True, extra="allow")

    call_id: str
    from_number: str = Field(alias="from")
    to_number: str = Field(default="", alias="to")
    event_type: CallEventType = CallEventType.INCOMING
    timestamp: Optional[str] = None


class MangoWebhookPayload(BaseModel):
    """Raw form fields from the Mango POST request."""

    model_config = ConfigDict(frozen=True)

    vpbx_api_key: str
    sign: str
    json: str  # stringified JSON — parsed separately


class CallSession(BaseModel):
    """In-flight call state persisted in Redis."""

    model_config = ConfigDict(frozen=True)

    call_id: str
    caller_number: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    is_known_client: bool = False
    department: Optional[str] = None
    priority: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    transcript_chunks: list[str] = Field(default_factory=list)


class CallResult(BaseModel):
    """Final output after call processing completes."""

    model_config = ConfigDict(frozen=True)

    call_id: str
    caller_number: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    duration_seconds: int = 0
    transcript: str = ""
    classification: Optional[dict[str, Any]] = None
    task_id: Optional[str] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
