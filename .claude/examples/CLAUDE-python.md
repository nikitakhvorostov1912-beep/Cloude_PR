# {PROJECT_NAME}

## Стек
- Python 3.12+
- FastAPI с типизацией Pydantic v2
- Async/await для I/O операций
- Логирование через стандартный logging

## Правила кода

### API
- Все ответы через Pydantic модели
- Обработка ошибок: HTTPException с русскими сообщениями
- Валидация входных данных через Pydantic
- Async handlers для I/O операций

### Структура
```
app/
├── main.py        # FastAPI app, middleware, CORS
├── config.py      # Settings через Pydantic BaseSettings
├── models/        # Pydantic модели (request/response)
├── routes/        # API роуты (по домену)
├── services/      # Бизнес-логика
└── utils/         # Утилиты
```

### Стиль
- Type hints обязательны
- Docstrings для публичных функций
- Функции < 50 строк, файлы < 400 строк
- `from __future__ import annotations` в каждом файле
- Ранний возврат вместо глубокой вложенности

## Тесты

```bash
pytest tests/ -v
```
- pytest + httpx (AsyncClient) для API тестов
- Минимум 80% покрытие
- Фикстуры в `conftest.py`

## Запуск

```bash
cd {PROJECT_PATH}
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Переменные окружения

```bash
# .env.example
DEBUG=true
APP_TITLE={PROJECT_NAME}
```

## Перед коммитом
- `pytest tests/ -v` — все тесты проходят
- Нет `print()` в production-коде
- Все API эндпоинты обрабатывают ошибки
