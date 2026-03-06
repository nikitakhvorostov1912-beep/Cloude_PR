# .claude/ — Карта проекта

> Быстрый справочник: что где лежит, как добавить, как использовать.

## Структура

```
.claude/
├── INDEX.md              ← Этот файл
├── BACKLOG.md            ← Список инструментов к установке / на заметке
├── launch.json           ← Конфигурация dev-серверов (Preview)
├── settings.local.json   ← Локальные настройки Claude Code
│
├── agents/               ← Субагенты (33 шт.)
│   ├── *.md              ← 17 кастомных агентов
│   └── ecc/              ← 16 агентов из Everything Claude Code
│
├── commands/             ← Slash-команды
│   └── ecc/              ← 40 команд ECC (/ecc:plan, /ecc:tdd, /ecc:claw...)
│
├── skills/               ← Скиллы (141 шт.)
│   ├── [custom]/         ← 44 кастомных скилла
│   ├── ecc/              ← 65 скиллов ECC
│   └── marketing/        ← 32 маркетинговых скилла
│
├── rules/                ← Правила кодинга
│   └── ecc/common/       ← Coding style, testing, security, git...
│
├── memory/               ← Долгосрочная память (3 уровня)
│   └── categories/       ← tech-stack, preferences, decisions, credentials
│
├── plans/                ← Сессионное планирование (шаблоны)
│
├── hooks/                ← Хуки (Stop, SubagentStop)
│   └── ecc/
│
├── scripts/              ← Скрипты (CI, хуки, кодмэпы)
│   └── ecc/
│
├── plugins/              ← Плагины (Composio)
│   └── connect-apps-plugin/
│
├── mcp-configs/          ← MCP-серверы
│   └── mcp-servers.json
│
├── examples/             ← Примеры CLAUDE.md для разных стеков
└── worktrees/            ← Рабочие деревья git
```

---

## Агенты (33)

### Кастомные (17) — `.claude/agents/`

| Агент | Когда использовать |
|-------|-------------------|
| **code-reviewer** | После написания кода — полный ревью 🔴🟡🟢 |
| **bug-hunter** | Баг, тест падает, что-то не работает |
| **code-scout** | ПЕРЕД задачей — разведка архитектуры |
| **deep-researcher** | Глубокое исследование любой темы (5+ запросов) |
| **research-fetcher** | Субагент deep-researcher для batch-загрузки URL |
| **pre-commit-guard** | Автопроверка перед коммитом (pytest, build, console.error) |
| **performance-engineer** | Узкие места, профилирование, нагрузочное тестирование |
| **api-designer** | REST/GraphQL дизайн, OpenAPI, версионирование |
| **docker-expert** | Docker оптимизация, multi-stage, безопасность |
| **mcp-developer** | MCP-серверы и клиенты |
| **devops-engineer** | CI/CD, IaC, контейнеризация |
| **prompt-engineer** | Дизайн и оптимизация промптов |
| **artifact-validator** | Валидация BPMN JSON, Visio |
| **bpm-architect** | Полный аудит и исправление BPMN-процессов |
| **bpm-json-auditor** | Глубокий аудит BPMN JSON |
| **bpm-svg-validator** | Проверка SVG-диаграмм |
| **bpm-visio-checker** | Проверка Visio (.vsdx) файлов |

### ECC (16) — `.claude/agents/ecc/`

| Агент | Когда использовать |
|-------|-------------------|
| **planner** | Планирование сложных фич |
| **architect** | Архитектурные решения |
| **tdd-guide** | TDD-подход: тесты → код |
| **code-reviewer** | Ревью кода (ECC версия) |
| **security-reviewer** | Безопасность перед коммитами |
| **build-error-resolver** | Когда билд падает |
| **e2e-runner** | E2E-тесты (Playwright) |
| **refactor-cleaner** | Удаление мёртвого кода |
| **doc-updater** | Обновление документации |
| **database-reviewer** | PostgreSQL, оптимизация SQL |
| **python-reviewer** | Python code review (PEP 8) |
| **go-reviewer** | Go code review |
| **go-build-resolver** | Go build ошибки |
| **chief-of-staff** | Email/Slack/Messenger триаж |
| **harness-optimizer** | Оптимизация agent harness |
| **loop-operator** | Управление автономными циклами |

---

## Скиллы — Ключевые

### Наши кастомные (Survey Automation)

| Скилл | Описание |
|-------|---------|
| `1c-survey-methodology` | Методология предпроектного обследования |
| `process-extraction` | Извлечение BPMN из интервью |
| `gap-analysis` | GAP-анализ AS-IS vs типовой функционал |
| `to-be-optimization` | Оптимизация TO-BE процессов |
| `requirements-list` | FR/NFR/IR с MoSCoW приоритизацией |
| `quality-gate` | Полная проверка проекта — PASS/FAIL |
| `health-check` | Быстрая проверка: сервер, фронт, API |
| `memory-management` | 3-уровневая система памяти + сессионное планирование |

### Генерация документов

| Скилл | Описание |
|-------|---------|
| `word-generation` | Word (.docx) через python-docx |
| `excel-generation` | Excel (.xlsx) через openpyxl |
| `pptx-generation` | PowerPoint через python-pptx |
| `visio-generation` | Visio (.vsdx) BPMN-диаграммы |

### Разработка

| Скилл | Описание |
|-------|---------|
| `code-review` | Полный code review |
| `debug` | Системная отладка |
| `smart-fix` | Автоисправление с контекстом |
| `lint-check` | Линтинг Python + TypeScript |
| `e2e-test` | E2E-тесты Playwright |
| `ui-ux-review` | Проверка UI/UX |
| `research` | Глубокое исследование темы |

### ECC — Ключевые

| Скилл | Описание |
|-------|---------|
| `ecc/strategic-compact` | Стратегическое сжатие контекста + 5-Question Reboot |
| `ecc/continuous-learning` | Извлечение паттернов + 3-Strike Protocol |
| `ecc/tdd-workflow` | TDD-процесс RED→GREEN→REFACTOR |
| `ecc/python-patterns` | Паттерны Python |
| `ecc/frontend-patterns` | Паттерны фронтенда |
| `ecc/security-review` | Безопасность |

---

## Как добавить

### Новый агент
```bash
# Создать файл в agents/
.claude/agents/my-agent.md

# Формат:
---
name: my-agent
description: "Когда использовать этот агент"
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
maxTurns: 25
---
[системный промпт]
```

### Новый скилл
```bash
# Создать папку и SKILL.md
.claude/skills/my-skill/SKILL.md

# Формат:
---
name: my-skill
description: Краткое описание для автообнаружения
---
[содержимое скилла]
```

### Новая запись в память
```bash
# Факт → memory/categories/[тема].md
# Или новый файл в memory/categories/
```

### Новый инструмент в бэклог
```bash
# Добавить запись в BACKLOG.md
### N. Название — Краткое описание
- **Репо:** URL
- **Что:** ...
- **Приоритет:** 🔴 Высокий | 🟡 Средний | 🔵 Низкий
- **Статус:** ⏳ На заметке
```

---

*Обновлено: 2026-03-06 | Агентов: 33 | Скиллов: 141 | Команд: 40*
