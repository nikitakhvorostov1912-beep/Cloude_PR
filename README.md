# Cloude PR — AI-Powered Development Workspace

Рабочее пространство для AI-driven разработки с полной интеграцией Claude Code.

## Проекты

| Проект | Описание | Стек |
|--------|---------|------|
| **Survey Automation** | Автоматизация предпроектного обследования 1С | Python/FastAPI + Next.js 15 |
| **Voice Agent 1C** | Голосовой агент для интеграции с 1С | Python, Mango API |
| **Desktop Installer** | Windows Electron-приложение | Electron + Python |

## Структура

```
Cloude_PR/
├── projects/
│   └── survey-automation/   # Основной проект
│       ├── backend/         # FastAPI + Python 3.12
│       └── frontend/        # Next.js 15 + React 19
│
├── voice-agent-1c/          # Голосовой агент
├── desktop/                 # Desktop-версия (Electron)
│
├── .claude/                 # Claude Code конфигурация
│   ├── agents/              # 33 субагента
│   ├── skills/              # 141 скилл
│   ├── commands/            # 40 slash-команд
│   ├── memory/              # Долгосрочная память
│   ├── plans/               # Шаблоны сессионного планирования
│   ├── INDEX.md             # Карта всего содержимого
│   └── BACKLOG.md           # Бэклог инструментов
│
├── .agents/                 # Anthropic plugin-скиллы
├── CLAUDE.md                # Правила проекта
└── .gitignore
```

## Быстрый старт

```bash
# Survey Automation
cd projects/survey-automation && start.bat

# Или раздельно:
cd projects/survey-automation/backend && uvicorn main:app --reload
cd projects/survey-automation/frontend && npm run dev
```

## Claude Code Setup

Workspace полностью настроен для работы с Claude Code:
- **33 агента** — code-reviewer, bug-hunter, deep-researcher, performance-engineer и др.
- **141 скилл** — от генерации документов до маркетинга
- **40 команд** — /ecc:plan, /ecc:tdd, /ecc:quality-gate и др.
- **Память** — 3-уровневая иерархия с автосохранением
- **Планирование** — Per-task files + 5-Question Reboot

Подробнее: `.claude/INDEX.md`

## Технологии

- **Backend:** Python 3.12, FastAPI, Pydantic v2
- **Frontend:** Next.js 15, React 19, TypeScript, shadcn/ui, Tailwind CSS 4
- **AI:** Claude Code (Opus 4.6), 33 субагента, MCP (Composio)
- **Данные:** JSON + файловая система
