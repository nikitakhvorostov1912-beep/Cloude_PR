---
name: project-init
description: Инициализация нового проекта в workspace. Создаёт структуру папок, CLAUDE.md по стеку, launch.json. Используй когда нужно начать новый проект.
---

# Скилл: Инициализация нового проекта

## Когда использовать
- Пользователь начинает новый проект
- Нужно создать структуру для нового приложения/сервиса
- Переход к работе над новым компонентом в workspace

## Процесс

### Шаг 1. Спроси у пользователя

Задай 3 вопроса (используй AskUserQuestion):

1. **Название проекта** — kebab-case, будет именем папки (например: `my-crm`, `analytics-dashboard`)
2. **Стек** — выбор из:
   - `python` — FastAPI + Pydantic v2
   - `nodejs` — Next.js 15 + React 19 + TypeScript
   - `fullstack` — Python backend + Next.js frontend
   - `1c` — 1С:Предприятие (BSL + XML)
3. **Расположение** — где создать:
   - `projects/{name}/` (по умолчанию)
   - Или произвольный путь

### Шаг 2. Создай структуру

#### Для `python`:
```
{project}/
├── CLAUDE.md          <- из шаблона CLAUDE-python.md
├── app/
│   ├── __init__.py
│   ├── main.py        <- FastAPI app
│   ├── config.py      <- Settings через Pydantic
│   ├── models/        <- Pydantic модели
│   ├── routes/        <- API эндпоинты
│   └── services/      <- Бизнес-логика
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── requirements.txt
└── .env.example
```

#### Для `nodejs`:
```
{project}/
├── CLAUDE.md          <- из шаблона CLAUDE-nodejs.md
├── src/
│   ├── app/           <- Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/    <- UI компоненты
│   ├── lib/           <- Утилиты
│   └── types/         <- TypeScript типы
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── .env.example
```

#### Для `fullstack`:
```
{project}/
├── CLAUDE.md          <- комбинированный шаблон
├── backend/           <- структура python
│   └── ...
├── frontend/          <- структура nodejs
│   └── ...
└── start.bat          <- запуск обоих серверов
```

#### Для `1c`:
```
{project}/
├── CLAUDE.md          <- из шаблона CLAUDE-1c.md
├── src/
│   └── cf/            <- XML-выгрузка конфигурации
├── cfe/               <- Расширения
├── epf/               <- Внешние обработки
├── erf/               <- Внешние отчёты
├── docs/              <- Документация
└── .v8-project.json   <- Реестр баз (для db-list)
```

### Шаг 3. Скопируй CLAUDE.md по стеку

Читай шаблон из `.claude/examples/CLAUDE-{стек}.md` и копируй в `{project}/CLAUDE.md`.
Замени плейсхолдеры:
- `{PROJECT_NAME}` -> название проекта
- `{PROJECT_PATH}` -> путь к проекту

### Шаг 4. Обнови launch.json (если есть dev-сервер)

Для `python` добавь:
```json
{
  "name": "{name}-backend",
  "runtimeExecutable": "python",
  "runtimeArgs": ["-m", "uvicorn", "app.main:app", "--reload", "--port", "{port}"],
  "port": {port}
}
```

Для `nodejs` добавь:
```json
{
  "name": "{name}-frontend",
  "runtimeExecutable": "npm",
  "runtimeArgs": ["run", "dev"],
  "port": {port}
}
```

Порт выбирай автоматически (3000, 3001, 3002... или 8000, 8001, 8002...), проверяя что не занят.

### Шаг 5. Финальный отчёт

Выведи:
```
Проект {name} создан:
- Путь: {path}
- Стек: {stack}
- CLAUDE.md: настроен
- Launch: настроен (порт {port})

Команды:
  /health-check    — проверить что всё работает
  /quality-gate    — полная проверка перед сдачей
```

## Важно
- Все тексты на русском языке
- Не создавай файлы которые не нужны стеку
- Не добавляй зависимости — пользователь установит сам
- Используй относительные пути в CLAUDE.md
