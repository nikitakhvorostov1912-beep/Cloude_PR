"""Pydantic модели: звонки и данные Mango Office.

Все модели используют Pydantic v2 с ConfigDict(from_attributes=True).
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CallEventType(StrEnum):
    """Типы событий Mango Office."""

    INCOMING = "call.incoming"
    CONNECTED = "call.connected"
    COMPLETED = "call.completed"


class CallDirection(StrEnum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class MangoCallEvent(BaseModel):
    """Разбор события звонка из JSON тела Mango webhook.

    Поля соответствуют формату Mango Office VPBX API.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    entry_id: str = Field(..., description="ID записи в Mango")
    call_id: str = Field(..., description="ID звонка")
    timestamp: int = Field(..., description="Unix timestamp события")
    seq: int = Field(default=0, description="Порядковый номер события")
    call_state: str = Field(default="", description="Состояние звонка")
    location: str = Field(default="", description="Локация")
    from_number: str = Field(default="", alias="from", description="Номер звонящего")
    to_number: str = Field(default="", alias="to", description="Номер назначения")
    to_extension: str = Field(default="", description="Внутренний номер")
    line_number: str = Field(default="", description="Номер линии")
    dct_type: int = Field(default=0, description="Тип DCT")


class MangoWebhookPayload(BaseModel):
    """POST тело запроса от Mango Office.

    Формат: vpbx_api_key + sign + json (строка).
    Подпись: sha256(vpbx_api_key + json + vpbx_api_salt).
    """

    vpbx_api_key: str = Field(..., description="API ключ VPBX")
    sign: str = Field(..., description="SHA-256 подпись запроса")
    json: str = Field(..., description="JSON-строка с данными события")


class CallSession(BaseModel):
    """Активная сессия звонка (хранится в Redis)."""

    model_config = ConfigDict(from_attributes=True)

    call_id: str = Field(..., description="ID звонка Mango")
    caller_number: str = Field(..., description="Номер звонящего")
    started_at: datetime = Field(..., description="Время начала")

    # Данные из 1С
    client_id: str | None = Field(default=None, description="ID клиента в 1С")
    client_name: str | None = Field(default=None, description="Имя клиента")
    is_known_client: bool = Field(default=False, description="Известный клиент")

    # Состояние
    state: str = Field(default="ringing", description="ringing|connected|completed")


class CallResult(BaseModel):
    """Итоговый результат звонка."""

    model_config = ConfigDict(from_attributes=True)

    call_id: str
    caller_number: str
    client_id: str | None = None
    client_name: str | None = None
    is_known_client: bool = False
    task_id: str | None = None
    department: str | None = None
    priority: str | None = None
    duration_seconds: int | None = None
    transcript_summary: str | None = None
