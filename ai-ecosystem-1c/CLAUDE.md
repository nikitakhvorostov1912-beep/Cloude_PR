# AI Ecosystem 1C — Phase 1 (Суфлёр)

## Описание
AI-панель суфлёра для менеджера техподдержки франчайзи 1С.
Real-time транскрипт, автоклассификация обращений, создание задач в Sakura CRM.

## Архитектура
Clean Architecture + DDD-lite:
- `orchestrator/` — FastAPI routes, WebSocket, DI, middleware
- `agents/` — AI agents (voice, classifier), business logic
- `services/` — STT/TTS/LLM/notifications adapters
- `integrations/` — external clients (Mango, 1C, Sakura)
- `models/` — Pydantic API models + SQLAlchemy ORM
- `database/` — connection, Alembic migrations
- `dashboard/` — Next.js 15 frontend (Void Violet design)

## Запуск
```bash
# Backend
pip install -r requirements.txt
python -m uvicorn orchestrator.main:app --reload --port 8000

# Frontend
cd dashboard && npm install && npm run dev

# Или всё сразу
start.bat
```

## Тесты
```bash
python -m pytest tests/ -v
python -m pytest tests/ --cov=. --cov-report=term-missing
```

## Ключевые файлы
- `orchestrator/config.py` — вся конфигурация (Pydantic Settings v2)
- `orchestrator/main.py` — FastAPI app factory + lifespan
- `agents/classifier/routing_rules.py` — детерминированная маршрутизация
- `agents/classifier/agent.py` — двухфазный классификатор (rules → LLM)
- `agents/voice_agent/agent.py` — голосовой диалог
- `agents/voice_agent/dialogue_manager.py` — FSM состояний

## API Endpoints
- `GET /health` — health check
- `POST /webhooks/mango/incoming` — Mango Office webhook
- `WS /ws/call/{call_id}` — real-time call updates
- `GET /api/dashboard/kpis` — KPI данные
- `GET /api/dashboard/calls` — список звонков
- `GET /api/dashboard/calls/{id}` — детали звонка

## Дизайн: Void Violet
- Тема: тёмная (#0a0a0f), акцент violet (#8b5cf6)
- Glassmorphism cards + Bento Grid
- Gradient mesh фон
- Animated KPI с count-up
- Command Palette (Cmd+K)

## Перед коммитом
- `pytest tests/ -v` — все тесты зелёные
- `cd dashboard && npm run build` — без ошибок
