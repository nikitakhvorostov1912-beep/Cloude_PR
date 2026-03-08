"""Скрипт для заполнения БД демо-данными.

Запуск:
    cd voice-agent-1c
    venv\\Scripts\\python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base, CallLog, Transcript

# ── Конфигурация ──────────────────────────────────────────────
DATABASE_URL = "sqlite+aiosqlite:///./demo.db"

DEPARTMENTS = ["support", "development", "implementation", "presale", "specialist"]
PRIORITIES = ["critical", "high", "normal", "low"]
EVENT_TYPES = ["summary", "call"]
DIRECTIONS = ["incoming"]
PRODUCTS = ["БП", "КА", "ЗУП", "УТ", "Розница", "ERP", "Кастомная"]
TASK_TYPES = ["error", "consult", "feature", "update", "project"]

CLIENT_NAMES = [
    "ООО Ромашка", "ИП Иванов", "АО Гамма-Софт", "ООО ТехноПлюс",
    "ЗАО Инфотех", "ООО Бизнес-Консалт", "ИП Петров", "ООО АльфаТрейд",
    "ООО Сигма", "АО МегаСервис", "ООО ДельтаПро", "ИП Сидорова",
    "ООО КомТех", "ЗАО ИнноваТех", "ООО СтройМастер", None, None, None,
]

PHONE_NUMBERS = [
    "+79161234567", "+79261234568", "+79031234569", "+79101234570",
    "+79151234571", "+79201234572", "+79301234573", "+79501234574",
    "+79601234575", "+79701234576", "+79801234577", "+79111234578",
    "+79121234579", "+79131234580", "+79141234581", "+79171234582",
]

TRANSCRIPT_SEGMENTS = [
    [
        {"speaker": "agent", "text": "Здравствуйте, компания 1С-Франчайзи, чем могу помочь?", "start_time": 0.0},
        {"speaker": "client", "text": "Добрый день! У нас проблема с обновлением Бухгалтерии. После обновления не формируется баланс.", "start_time": 3.2},
        {"speaker": "agent", "text": "Понимаю. Какая версия конфигурации у вас установлена?", "start_time": 12.5},
        {"speaker": "client", "text": "Бухгалтерия предприятия 3.0, релиз 3.0.165", "start_time": 16.8},
        {"speaker": "agent", "text": "Хорошо, создаю заявку на отдел поддержки с высоким приоритетом. Специалист свяжется с вами в течение часа.", "start_time": 21.3},
        {"speaker": "client", "text": "Спасибо большое!", "start_time": 28.1},
    ],
    [
        {"speaker": "agent", "text": "Добрый день! Компания 1С-Франчайзи, слушаю вас.", "start_time": 0.0},
        {"speaker": "client", "text": "Здравствуйте, нам нужна консультация по переходу с УТ 10 на УТ 11.", "start_time": 2.8},
        {"speaker": "agent", "text": "Отличный вопрос! Могу уточнить, сколько пользователей работают в текущей системе?", "start_time": 9.5},
        {"speaker": "client", "text": "Около пятнадцати человек, плюс склад — ещё пять.", "start_time": 14.2},
        {"speaker": "agent", "text": "Понятно. Переведу вас на отдел внедрения, они подготовят предварительную оценку проекта.", "start_time": 19.7},
        {"speaker": "client", "text": "Хорошо, жду.", "start_time": 26.3},
    ],
    [
        {"speaker": "agent", "text": "Здравствуйте! Техническая поддержка 1С, как могу помочь?", "start_time": 0.0},
        {"speaker": "client", "text": "У нас зависает ЗУП при расчёте зарплаты. Уже третий день не можем закрыть период.", "start_time": 3.0},
        {"speaker": "agent", "text": "Это критично. Уточните — зависает при расчёте конкретного подразделения или всей организации?", "start_time": 10.5},
        {"speaker": "client", "text": "Всей организации. У нас 500 сотрудников.", "start_time": 16.2},
        {"speaker": "agent", "text": "Срочная заявка создана. Специалист подключится удалённо в течение 30 минут.", "start_time": 20.8},
    ],
    [
        {"speaker": "agent", "text": "Компания 1С-Франчайзи, добрый день!", "start_time": 0.0},
        {"speaker": "client", "text": "Добрый день. Хотел бы узнать стоимость внедрения ERP для производственного предприятия.", "start_time": 2.5},
        {"speaker": "agent", "text": "Конечно! Расскажите, пожалуйста, о масштабе предприятия — количество сотрудников и основные направления.", "start_time": 8.3},
        {"speaker": "client", "text": "300 человек, производство пищевой продукции, три цеха, склад и офис.", "start_time": 14.0},
        {"speaker": "agent", "text": "Отлично. Направлю вашу заявку в отдел предпродаж, они подготовят коммерческое предложение.", "start_time": 22.5},
    ],
]

SUMMARIES = [
    "Ошибка формирования баланса после обновления БП 3.0.165. Клиент не может закрыть квартал.",
    "Консультация по миграции с УТ 10 на УТ 11. 20 пользователей, нужна оценка проекта.",
    "Критичная проблема: зависание ЗУП при расчёте зарплаты для 500 сотрудников.",
    "Запрос на коммерческое предложение по внедрению ERP для производства.",
    "Ошибка при проведении документов реализации в КА. Появляется после обновления.",
    "Не выгружается отчётность в ФНС через 1С-Отчётность. Срок сдачи через 2 дня.",
    "Консультация по настройке обмена между Розницей и УТ 11.",
    "Нужна доработка печатной формы счёт-фактуры под требования клиента.",
    "Проблема с лицензиями: программные ключи не активируются.",
    "Запрос на обучение сотрудников по работе в ЗУП 3.1.",
]


async def seed(session: AsyncSession) -> None:
    """Создаёт демо-данные: 50 звонков за последние 30 дней."""
    now = datetime.now(timezone.utc)
    calls_created = 0

    for i in range(50):
        # Случайное время за последние 30 дней (рабочие часы)
        days_ago = random.randint(0, 29)
        hour = random.randint(8, 19)
        minute = random.randint(0, 59)
        call_time = now - timedelta(days=days_ago, hours=random.randint(0, 5))
        call_time = call_time.replace(hour=hour, minute=minute)

        duration = random.randint(30, 600)
        department = random.choice(DEPARTMENTS)
        priority = random.choice(PRIORITIES)
        has_task = random.random() > 0.25  # 75% создают задачу
        client_name = random.choice(CLIENT_NAMES)
        is_known = client_name is not None

        call = CallLog(
            id=str(uuid.uuid4()),
            mango_call_id=f"mango-demo-{i + 1:03d}",
            caller_number=random.choice(PHONE_NUMBERS),
            called_number="+74951234567",
            event_type=random.choice(EVENT_TYPES),
            direction="incoming",
            client_name=client_name,
            is_known_client=is_known,
            task_id=f"TASK-{random.randint(1000, 9999)}" if has_task else None,
            department=department,
            priority=priority,
            duration_seconds=duration,
            call_started_at=call_time,
            call_ended_at=call_time + timedelta(seconds=duration),
            created_at=call_time,
        )
        session.add(call)

        # Добавляем транскрипцию для ~60% звонков
        if random.random() > 0.4:
            segments = random.choice(TRANSCRIPT_SEGMENTS)
            product = random.choice(PRODUCTS)
            task_type = random.choice(TASK_TYPES)

            transcript = Transcript(
                id=str(uuid.uuid4()),
                call_log_id=call.id,
                full_text=" ".join(seg["text"] for seg in segments),
                segments=segments,
                classification={
                    "product": product,
                    "task_type": task_type,
                    "confidence": round(random.uniform(0.6, 0.99), 2),
                    "summary": random.choice(SUMMARIES),
                },
                confidence=round(random.uniform(0.6, 0.99), 2),
                duration_seconds=float(duration),
                created_at=call_time,
            )
            session.add(transcript)

        calls_created += 1

    await session.commit()
    print(f"Создано {calls_created} демо-звонков с транскрипциями")


async def main() -> None:
    """Точка входа: создаём таблицы и заполняем данными."""
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблицы созданы")

    # Очищаем старые данные
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM transcripts"))
        await conn.execute(text("DELETE FROM call_logs"))
    print("Старые данные очищены")

    # Сеем данные
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)

    await engine.dispose()
    print("Готово! Запустите бэкенд и откройте дашборд.")


if __name__ == "__main__":
    asyncio.run(main())
