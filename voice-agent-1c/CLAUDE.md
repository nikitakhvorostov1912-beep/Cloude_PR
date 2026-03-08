# Правила проекта Voice Agent 1C

## Обязательные требования

- Python 3.12, FastAPI 0.115, Pydantic v2
- Все API ответы через Pydantic модели
- Async/await для всех I/O операций — НИКОГДА не блокирующие вызовы в async
- Обработка ошибок на каждом уровне с русскими сообщениями
- Все тексты/строки для пользователя на русском языке
- Type hints обязательны для всех функций

## Архитектура

```
Mango Office WebHook → FastAPI → STT (Yandex) → Claude AI → TTS (Yandex) → 1C Task
                                                                          → Telegram/SMS
```

### Модули
| Модуль | Назначение |
|--------|-----------|
| `orchestrator/` | FastAPI app, config, session, routing |
| `services/` | Бизнес-логика: AI, STT, TTS, уведомления |
| `integrations/` | Внешние сервисы: Mango, 1C |
| `core/` | FSM (state machine) |
| `database/` | SQLAlchemy модели + Alembic миграции |
| `api/routes/` | WebSocket, Dashboard API |
| `models/` | Pydantic схемы |
| `prompts/` | Системные промпты для Claude |

## Перед каждым коммитом

```bash
cd voice-agent-1c
venv/Scripts/python.exe -m pytest tests/ -v  # 180 тестов, все должны пройти
```

## Запуск

```bash
cd voice-agent-1c
venv\Scripts\activate
uvicorn orchestrator.main:app --reload --host 0.0.0.0 --port 8000
```

## Конфигурация

Все настройки через `.env` (см. `.env.example`). НИКОГДА не хардкодить секреты.

Ключевые переменные:
- `MANGO_API_KEY`, `MANGO_WEBHOOK_SECRET` — телефония
- `ONEC_BASE_URL`, `ONEC_USERNAME`, `ONEC_PASSWORD` — интеграция 1С
- `DATABASE_URL` — PostgreSQL (asyncpg)
- `REDIS_URL` — сессии
- `YANDEX_API_KEY`, `YANDEX_FOLDER_ID` — STT/TTS
- `ANTHROPIC_API_KEY` — Claude AI
- `ALLOWED_ORIGINS` — CORS (по умолчанию localhost:3000)

## Миграции БД

```bash
alembic upgrade head          # применить
alembic revision --autogenerate -m "описание"  # создать новую
```

## Тестирование

- Фреймворк: pytest + pytest-asyncio
- Моки: in-memory SQLite (aiosqlite), fakeredis, pytest-httpx
- Минимум 80% покрытия
- Тесты пишутся ПЕРЕД реализацией (TDD)

## Данные

- PostgreSQL для CallLog, Transcript
- Redis для сессий (TTL 30 мин)
- Файловая система для аудио-записей
