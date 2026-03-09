# Правила проекта Survey Automation

## Обязательные требования

- Каждый UI элемент ДОЛЖЕН быть функциональным (никаких заглушек, TODO, placeholder)
- Каждая кнопка ДОЛЖНА выполнять действие
- Каждый API endpoint ДОЛЖЕН быть реализован и обрабатывать ошибки
- Все тексты интерфейса на русском языке
- Тёмная тема по умолчанию, все компоненты стилизованы
- Перед сдачей: запустить `/quality-gate` и получить PASS

## Перед каждым коммитом

- Запустить backend тесты: `cd projects/survey-automation/backend && pytest tests/ -v`
- Запустить frontend build: `cd projects/survey-automation/frontend && npm run build` (без ошибок)
- Проверить через Preview что UI работает
- Нет `console.error` в браузере

## Структура кода

### Backend (Python)
- FastAPI с типизацией Pydantic v2
- Все API ответы через Pydantic модели
- Обработка ошибок на каждом уровне (HTTPException с русскими сообщениями)
- Async/await для I/O операций
- Логирование через стандартный logging

### Frontend (TypeScript)
- Next.js 15 (App Router)
- React 19
- shadcn/ui для компонентов
- Tailwind CSS 4
- TanStack Query для кэширования API
- Все тексты на русском

## Запуск

```bash
cd projects/survey-automation && start.bat
```

## Данные

- Все данные предоставляются пользователем через веб-интерфейс
- Хранение: JSON + папки в `backend/data/projects/`
- Без авторизации, без БД
