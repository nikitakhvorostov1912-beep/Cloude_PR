# Claude Code Workspace

> Универсальное рабочее пространство для разработки с Claude Code.
> Проектно-специфичные правила — в `CLAUDE.md` каждого проекта.

## Общие правила

- Все тексты интерфейса и документации на русском языке
- Тёмная тема по умолчанию
- Каждый UI элемент ДОЛЖЕН быть функциональным (никаких заглушек, TODO, placeholder)
- Каждый API endpoint ДОЛЖЕН быть реализован и обрабатывать ошибки
- Перед сдачей: запустить `/quality-gate` и получить PASS

## Структура workspace

```
D:\Cloude_PR\
├── projects/              ← Проекты (каждый со своим CLAUDE.md)
│   ├── survey-automation/ ← Survey Automation (FastAPI + Next.js)
│   └── ...
├── voice-agent-1c/        ← Voice Agent 1C
├── ai-ecosystem-1c/       ← AI Ecosystem 1C
├── .claude/               ← Агенты, скиллы, правила, память
│   ├── INDEX.md           ← Карта всего workspace
│   └── BACKLOG.md         ← Очередь инструментов к установке
└── tools/                 ← Внешние инструменты (MCP RAQ, Fragments)
```

## Инициализация нового проекта

```bash
/project-init
```

Создаёт структуру проекта, CLAUDE.md по стеку, launch.json.

## Ключевые команды

| Команда | Описание |
|---------|---------|
| `/quality-gate` | Полная проверка проекта — PASS/FAIL |
| `/health-check` | Быстрая проверка: сервер, фронт, API |
| `/code-review` | Ревью кода |
| `/debug` | Системная отладка |
| `/research` | Глубокое исследование темы |
| `/project-init` | Инициализация нового проекта |

## Перед каждым коммитом

- Запустить тесты проекта
- Проверить билд (без ошибок)
- Проверить через Preview что UI работает
- Нет `console.error` в браузере

## Чек-лист 8.5-совместимости (для CFE/УТ)

Клиенты УТ начнут переходить на 1С 8.5.x летом 2026. Перед merge `feature/*` в `master` для Русского_Транзита:

1. Smoke-тест на стенде 8.5.1 (отдельный `InfoBase5_8.5/`) — расширение применяется без ошибок
2. Тёмная тема — формы рендерятся читаемо
3. Плотные ТЧ (УстановкаЦен, Поручительства) не «ломаются» на новом UI
4. `tests/verification/run-all-tests.bsl` зелёный на 8.5
5. Двойной клик не используется как primary-trigger (8.5 их сокращает)

Если хоть один пункт красный — feature/* НЕ мержится без явного approval.

## AI-аугментированная разработка 1С

- **Правило 3 итераций (Матаков)** — `rules/1c/1c-ai-collaboration.md`. Не закрыли за 3 раунда → переписать вручную.
- **Чек-лист сдачи AI-кода** — `rules/1c/1c-rules.md` (8 пунктов: bsl-lint → A1-A11 → MCP → smoke → YAxUnit → cfe-validate → form-validate → явное «не верифицировано»).
- **AI-антипаттерны A1-A11** — `rules/1c/1c-anti-patterns.md`. Проверять через Grep после каждой генерации.
- **Spec-Driven Development** — Phase 0 в `1c-feature-dev` для Средней/Сложной/Критичной задачи.
- **autoMode.hard_deny** в `.claude/settings.local.json` — DESIGNER физически заблокирован, правка `upload/` и `ut-ext/` запрещена.

---

## Karpathy Skills

4 принципа кодинга (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) глобализованы в `~/.claude/CLAUDE.md` → секция «Karpathy Skills». Применяются ко всем проектам.

Самопроверка дифа: `/karpathy-check` (русский алиас: `/karpathy-proverka`).
