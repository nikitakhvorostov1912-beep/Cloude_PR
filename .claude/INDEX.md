# .claude/ — Карта проекта

> Быстрый справочник: что где лежит, как добавить, как использовать.

## Структура

```
.claude/
├── INDEX.md              <- Этот файл
├── BACKLOG.md            <- Список инструментов к установке / на заметке
├── launch.json           <- Конфигурация dev-серверов (Preview)
├── settings.local.json   <- Локальные настройки Claude Code
│
├── agents/               <- Субагенты (42 шт.)
│   ├── *.md              <- 26 кастомных агентов
│   └── ecc/              <- 16 агентов из Everything Claude Code
│
├── commands/             <- Slash-команды
│   └── ecc/              <- 40 команд ECC (/ecc:plan, /ecc:tdd, /ecc:claw...)
│
├── skills/               <- Скиллы (222 шт.)
│   ├── [custom]/         <- 125 кастомных скиллов
│   ├── ecc/              <- 65 скиллов ECC
│   └── marketing/        <- 32 маркетинговых скилла
│
├── rules/                <- Правила кодинга (34 файла)
│   ├── knowledge-router.md  <- Маршрутизатор памяти
│   ├── 1c/               <- 1С: стандарты BSL, оркестрация скиллов, UI
│   └── ecc/              <- common (9) + python/ts/go/swift (по 5)
│
├── memory/               <- Долгосрочная память (3 уровня)
│   └── categories/       <- tech-stack, preferences, decisions, credentials
│
├── plans/                <- Сессионное планирование
│   └── _templates/       <- task_plan, findings, progress
│
├── examples/             <- Шаблоны CLAUDE.md для новых проектов
│   ├── CLAUDE.md         <- Общий шаблон
│   ├── CLAUDE-python.md  <- Python (FastAPI/Django)
│   ├── CLAUDE-nodejs.md  <- Node.js (Next.js/Express)
│   └── CLAUDE-1c.md      <- 1С:Предприятие
│
├── plugins/              <- Плагины (Composio)
│   └── connect-apps-plugin/
│
├── mcp-configs/          <- MCP-серверы
│   └── mcp-servers.json
│
└── worktrees/            <- Рабочие деревья git
```

---

## Агенты (42)

### Выбор агента для исследования кода

| Задача | Агент | Модель | Скорость |
|--------|-------|--------|----------|
| Быстрый скан структуры, карта | `code-scout` | haiku | Быстро |
| Глубокий анализ одной фичи | `code-explorer` | sonnet | Средне |
| Проектирование архитектуры | `code-architect` | sonnet | Средне |
| Ревью написанного кода | `code-reviewer` | sonnet | Средне |
| Упрощение кода | `code-simplifier` | sonnet | Средне |

### Кастомные — `.claude/agents/`

| Агент | Когда использовать |
|-------|-------------------|
| **1С-разработка** | |
| `1c-code-architect` | Проектирование архитектуры 1С |
| `1c-code-explorer` | Анализ существующего кода 1С |
| `1c-code-reviewer` | Ревью кода 1С (+ MCP bsl-context) |
| `1c-code-simplifier` | Упрощение кода 1С |
| `1c-code-writer` | Написание BSL-кода 1С |
| **Разведка и исследование** | |
| `code-scout` | ПЕРЕД задачей — разведка архитектуры |
| `deep-researcher` | Глубокое исследование любой темы (5+ запросов) |
| `research-fetcher` | Субагент deep-researcher для batch-загрузки URL |
| **Код и ревью** | |
| `code-reviewer` | После написания кода — полный ревью |
| `bug-hunter` | Баг, тест падает, что-то не работает |
| `pre-commit-guard` | Автопроверка перед коммитом (pytest, build) |
| `rapid-prototyper` | Быстрое прототипирование |
| **Инфраструктура** | |
| `api-designer` | REST/GraphQL дизайн, OpenAPI |
| `docker-expert` | Docker оптимизация, multi-stage |
| `devops-engineer` | CI/CD, IaC, контейнеризация |
| `mcp-developer` | MCP-серверы и клиенты |
| `performance-engineer` | Профилирование, нагрузочное тестирование |
| `ai-engineer` | AI/ML инженерия |
| `prompt-engineer` | Дизайн и оптимизация промптов |
| **BPMN / визуализация** | |
| `bpm-architect` | Полный аудит и исправление BPMN-процессов |
| `bpm-json-auditor` | Глубокий аудит BPMN JSON |
| `bpm-svg-validator` | Проверка SVG-диаграмм |
| `bpm-visio-checker` | Проверка Visio (.vsdx) файлов |
| `artifact-validator` | Валидация BPMN JSON, Visio |
| **Оркестрация** | |
| `nexus-orchestrator` | Главный оркестратор |
| `sprint-prioritizer` | Приоритизация задач |

### ECC (16) — `.claude/agents/ecc/`

| Агент | Когда использовать |
|-------|-------------------|
| `planner` | Планирование сложных фич |
| `architect` | Архитектурные решения |
| `tdd-guide` | TDD-подход: тесты -> код |
| `code-reviewer` | Ревью кода (ECC версия) |
| `security-reviewer` | Безопасность перед коммитами |
| `build-error-resolver` | Когда билд падает |
| `e2e-runner` | E2E-тесты (Playwright) |
| `refactor-cleaner` | Удаление мёртвого кода |
| `doc-updater` | Обновление документации |
| `database-reviewer` | PostgreSQL, оптимизация SQL |
| `python-reviewer` | Python code review (PEP 8) |
| `go-reviewer` | Go code review |
| `go-build-resolver` | Go build ошибки |
| `chief-of-staff` | Email/Slack/Messenger триаж |
| `harness-optimizer` | Оптимизация agent harness |
| `loop-operator` | Управление автономными циклами |

---

## Скиллы — Ключевые

### Аналитика и обследование

| Скилл | Описание |
|-------|---------|
| `1c-survey-methodology` | Методология предпроектного обследования |
| `process-extraction` | Извлечение BPMN из интервью |
| `gap-analysis` | GAP-анализ AS-IS vs типовой функционал |
| `to-be-optimization` | Оптимизация TO-BE процессов |
| `requirements-list` | FR/NFR/IR с MoSCoW приоритизацией |
| `erp-configuration-advisor` | Подбор конфигурации 1С |
| `brainstorm` | Предварительная проработка идеи |

### 1С-экосистема (67 cc-1c-skills)

| Группа | Скиллы | Назначение |
|--------|--------|-----------|
| EPF | `epf-init`, `epf-add-form`, `epf-bsp-init`, `epf-bsp-add-command`, `epf-build`, `epf-dump`, `epf-validate` | Внешние обработки |
| ERF | `erf-init`, `erf-build`, `erf-dump`, `erf-validate` | Внешние отчёты |
| Form | `form-add`, `form-compile`, `form-edit`, `form-info`, `form-patterns`, `form-remove`, `form-validate` | Управляемые формы |
| SKD | `skd-compile`, `skd-edit`, `skd-info`, `skd-validate` | СКД |
| DB | `db-create`, `db-list`, `db-load-cf`, `db-load-xml`, `db-load-git`, `db-dump-cf`, `db-dump-xml`, `db-run`, `db-update` | Базы данных |
| CF | `cf-init`, `cf-edit`, `cf-info`, `cf-validate` | Конфигурации |
| CFE | `cfe-init`, `cfe-borrow`, `cfe-diff`, `cfe-patch-method`, `cfe-validate` | Расширения |
| Meta | `meta-compile`, `meta-edit`, `meta-info`, `meta-remove`, `meta-validate` | Объекты метаданных |
| Web | `web-info`, `web-publish`, `web-stop`, `web-test`, `web-unpublish` | Веб-публикация |
| Role | `role-compile`, `role-info`, `role-validate` | Роли и права |
| Subsystem | `subsystem-compile`, `subsystem-edit`, `subsystem-info`, `subsystem-validate` | Подсистемы |
| MXL | `mxl-compile`, `mxl-decompile`, `mxl-info`, `mxl-validate` | Табличные документы |
| Прочие | `help-add`, `img-grid`, `interface-edit`, `interface-validate`, `template-add`, `template-remove` | Справка, макеты |

### Генерация документов

| Скилл | Описание |
|-------|---------|
| `word-generation` | Word (.docx) через python-docx |
| `excel-generation` | Excel (.xlsx) через openpyxl |
| `pptx-generation` | PowerPoint через python-pptx |
| `visio-generation` | Visio (.vsdx) BPMN-диаграммы |
| `d3js-visualization` | D3.js интерактивные визуализации |

### Разработка и качество

| Скилл | Описание |
|-------|---------|
| `code-review` | Полный code review |
| `debug` | Системная отладка |
| `smart-fix` | Автоисправление с контекстом |
| `lint-check` | Линтинг Python + TypeScript |
| `e2e-test` | E2E-тесты Playwright |
| `ui-ux-review` | Проверка UI/UX |
| `quality-gate` | Полная проверка проекта — PASS/FAIL |
| `health-check` | Быстрая проверка: сервер, фронт, API |
| `research` | Глубокое исследование темы |
| `project-init` | Инициализация нового проекта |
| `memory-management` | 3-уровневая система памяти |

---

## Как добавить

### Новый проект
```bash
/project-init
# Выбрать стек -> создаст структуру + CLAUDE.md
```

### Новый агент
```bash
# Создать файл .claude/agents/my-agent.md
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
# Создать папку .claude/skills/my-skill/SKILL.md
---
name: my-skill
description: Краткое описание для автообнаружения
---
[содержимое скилла]
```

### Новая запись в память
```bash
# Факт -> memory/categories/[тема].md
# Или новый файл в memory/ + ссылка в knowledge-router.md
```

### Новый инструмент в бэклог
```bash
# Добавить запись в BACKLOG.md
### N. Название — Краткое описание
- **Репо:** URL
- **Что:** ...
- **Приоритет:** Высокий | Средний | Низкий
- **Статус:** Ожидает
```

---

*Обновлено: 2026-03-09 | Агентов: 42 | Скиллов: 222 | Правил: 34 | Команд: 40*
