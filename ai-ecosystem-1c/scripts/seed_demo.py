"""Seed demo data for development and demonstrations."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_engine, init_db
from models.db.call_log import CallLog
from models.db.transcript import Transcript
from models.db.classification import Classification


DEMO_CALLS = [
    {
        "caller_phone": "+74951234567",
        "client_name": "ООО Ромашка",
        "department": "support",
        "task_type": "error",
        "priority": "high",
        "product": "ЗУП",
        "summary": "Ошибка при формировании отчёта по зарплате",
        "transcript": "Клиент: Здравствуйте, у нас ошибка при формировании отчёта.\nОператор: Какая версия ЗУП?\nКлиент: 3.1.28, после обновления.",
    },
    {
        "caller_phone": "+74959876543",
        "client_name": "ИП Петров",
        "department": "development",
        "task_type": "feature",
        "priority": "normal",
        "product": "БП",
        "summary": "Доработка печатной формы счёта-фактуры",
        "transcript": "Клиент: Нужно доработать печатную форму.\nОператор: Расскажите подробнее.\nКлиент: Добавить дополнительные реквизиты.",
    },
    {
        "caller_phone": "+74955551234",
        "client_name": "ООО ТехноМир",
        "department": "implementation",
        "task_type": "update",
        "priority": "normal",
        "product": "КА",
        "summary": "Обновление КА до последней версии",
        "transcript": "Клиент: Хотим обновить Комплексную Автоматизацию.\nОператор: Какая текущая версия?\nКлиент: 2.5.14.",
    },
    {
        "caller_phone": "+78123332211",
        "client_name": "АО Сервис Плюс",
        "department": "support",
        "task_type": "consult",
        "priority": "low",
        "product": "УТ",
        "summary": "Консультация по настройке скидок",
        "transcript": "Клиент: Подскажите, как настроить скидки в УТ.\nОператор: Какой тип скидок вас интересует?\nКлиент: По объёму закупки.",
    },
]


async def seed() -> None:
    """Create demo call records."""
    await init_db()
    engine = get_engine()

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        now = datetime.now(timezone.utc)

        for i, demo in enumerate(DEMO_CALLS):
            call_id = f"demo-{uuid.uuid4().hex[:8]}"
            call_log = CallLog(
                call_id=call_id,
                caller_phone=demo["caller_phone"],
                called_number="+74951234500",
                client_name=demo["client_name"],
                department=demo["department"],
                status="completed",
                duration_seconds=120 + i * 60,
                started_at=now - timedelta(hours=i),
            )
            session.add(call_log)
            await session.flush()

            transcript = Transcript(
                call_log_id=call_log.id,
                full_text=demo["transcript"],
                dialogue=[
                    {"speaker": "client", "text": line.split(": ", 1)[1]}
                    if line.startswith("Клиент:")
                    else {"speaker": "operator", "text": line.split(": ", 1)[1]}
                    for line in demo["transcript"].split("\n")
                    if ": " in line
                ],
            )
            session.add(transcript)

            classification = Classification(
                call_log_id=call_log.id,
                department=demo["department"],
                department_confidence=0.88 + i * 0.02,
                task_type=demo["task_type"],
                task_type_confidence=0.85,
                priority=demo["priority"],
                priority_confidence=0.82,
                product=demo.get("product"),
                summary=demo["summary"],
                reasoning="Demo classification",
            )
            session.add(classification)

        await session.commit()
        print(f"Seeded {len(DEMO_CALLS)} demo calls")


if __name__ == "__main__":
    asyncio.run(seed())
