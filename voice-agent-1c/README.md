# Voice Agent 1C

Голосовой AI-агент для автоматического приёма и маршрутизации заявок франчайзи 1С.

## Быстрый старт

```bash
# 1. Запустить PostgreSQL и Redis
docker-compose up -d

# 2. Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать .env из шаблона
copy .env.example .env

# 5. Применить миграции
alembic upgrade head

# 6. Запустить сервер
uvicorn orchestrator.main:app --reload --host 0.0.0.0 --port 8000
```

## Архитектура

```
Клиент звонит -> Манго Офис (WebHook) -> FastAPI оркестратор
  -> Идентификация в 1С (HTTP)
  -> STT (Яндекс SpeechKit) -> AI (Claude) -> TTS (Яндекс)
  -> Создание задачи в 1С
  -> Уведомления (Telegram + SMS)
```

## API

- `GET /` — информация о сервисе
- `GET /api/health` — проверка здоровья
- `POST /api/v1/webhooks/mango/call` — вебхук входящего звонка

## Фазы разработки

1. **Фундамент** — FastAPI + PostgreSQL + Redis + Webhook + 1C клиент
2. **Голосовой диалог** — STT + Claude AI + TTS + WebSocket
3. **Уведомления** — Telegram + SMS + эскалация
4. **Качество** — аналитика + A/B тесты + оптимизация
