# Рабочая память проекта

## Проект
- **Название:** Cloude_PR (Survey Automation + Claude Code Workspace)
- **Ветка:** feature/workspace-setup
- **Платформа:** Windows 11, bash shell

## Стек
- Backend: Python 3.12, FastAPI, Pydantic v2
- Frontend: Next.js 15, React 19, TypeScript, shadcn/ui, Tailwind CSS 4
- Данные: JSON + файловая система (без БД)

## Инфраструктура Claude Code
- **Агенты:** 42 (26 кастомных + 16 ECC)
- **Скиллы:** 222 (125 кастомных + 65 ECC + 32 marketing)
- **Правила:** 1С-специфичные в `.claude/rules/1c/`
- **Команды:** 40 (ECC slash-commands)
- **Хуки:** Stop, SubagentStop (UserPromptSubmit удалён)
- **MCP:** Composio (500+ SaaS)
- **Карта проекта:** `.claude/INDEX.md`
- **Бэклог:** `.claude/BACKLOG.md`
- **Память:** `.claude/memory/categories/`
- **Шаблоны планов:** `.claude/plans/_templates/`

## Предпочтения пользователя
- Все тексты на русском
- Тёмная тема
- Краткие оценки "нужно / не нужно" перед установкой
- Не блокировать сообщения хуками
- Решения о установке принимает сам
- Инструменты записывать в BACKLOG.md

## Ключевые решения
- ECC в /ecc/ подпапках (не перезаписывать кастомное)
- maxTurns: 25 для всех агентов
- 2-Action Rule: после 2 поисков → сохрани находки
- 3-Strike Protocol: 3 разных попытки → эскалация
- 5-Question Reboot: после /compact обязательно

## CLI-инструменты
- Pake CLI v3.10.0, Xonsh v0.22.6, Claude Monitor v3.1.0, E2B Fragments, MCP RAQ 1C (`tools/mcp-raq-1c/`)

## Отладочные паттерны
- Аудио "play() OK но нет звука" → см. [debugging.md](debugging.md)
- Главные причины: тихие MP3 (-91dB от pedalboard), AudioContext suspended, setTimeout разрывает gesture
- ffmpeg volumedetect — быстрая проверка громкости файлов
- Preview/Playwright НЕ воспроизводят реальный звук — это нормально

## База знаний 1С
- Последовательности событий объектов → [1c-event-sequences.md](1c-event-sequences.md)
  - Проведение, отмена проведения, открытие форм, запись регистров
  - Источник: github.com/kuzyara/Sequences-of-events-for-1C-objects
- Протоколы обмена (CommerceML) → [1c-exchange-protocols.md](1c-exchange-protocols.md)
  - Этапы: группы → свойства → цены → каталог → предложения → документы
  - Интерфейсный подход: Group/Product/Offer/Document/Partner
  - Источник: github.com/carono/yii2-1c-exchange
- GitHub-инструменты для аналитика 1С → [1c-analyst-tools-github.md](1c-analyst-tools-github.md)
  - Вывод: на GitHub почти нет инструментов для аналитика 1С (только для разработчиков)
  - Лучшие: tools_ui_1c (984 stars, консоль запросов), StackTechnologies1C (386, каталог стека)
  - Наши скиллы закрывают больше задач аналитика, чем весь GitHub
  - ТЗ/обследование/BPMN для 1С — живёт на Infostart и у франчайзи, не на GitHub
- PDE — Prometheus Data Exporter для 1С → [1c-prometheus-pde.md](1c-prometheus-pde.md)
  - Встраиваемая конфигурация: HTTP-сервис для Prometheus scraping
  - Объекты: Справочник пэмМетрики, РС пэмСостояниеМетрик, HTTPService Prometheus
  - Регламентное задание для сбора метрик, форма настроек
  - Источник: github.com/freewms/PDE (126 звёзд)

## Промпт-инжиниринг
- Ролевые паттерны (180+ ролей) → [prompt-patterns.md](prompt-patterns.md)
  - Формат: Role → Task → Constraints → First request
  - Техники: boundary setting, output format lock, persona depth
  - Источник: github.com/f/prompts.chat
- Системные промпты AI-инструментов (31 продукт) → [system-prompts-reference.md](system-prompts-reference.md)
  - Cursor, Windsurf, Claude Code, v0, Lovable, Devin, Replit и др.
  - 7 паттернов: структура, tool docs, code changes, safety, memory, concise, planning
  - Источник: github.com/x1xhlol/system-prompts-and-models-of-ai-tools

## 1С-экосистема (полный стек)
- **Агенты**: 1c-code-explorer, 1c-code-architect, 1c-code-writer, 1c-code-reviewer, 1c-code-simplifier
- **Правила**: `.claude/rules/1c/1c-rules.md` (именование, запросы, клиент-сервер, БСП)
- **Скиллы (кастом)**: 1c-feature-dev, brainstorm, erp-configuration-advisor, gap-analysis, process-extraction, 1c-survey-methodology, to-be-optimization
- **Скиллы (cc-1c-skills, 67шт)**: epf-* (7), erf-* (4), form-* (6), skd-* (4), db-* (9), cf-* (4), cfe-* (5), meta-* (5), web-* (5), role-* (3), subsystem-* (4), mxl-* (4), help-add, img-grid, interface-*, template-*
- **Docs/Specs**: `docs/1c-specs/` (35 спецификаций XML-форматов 1С)
- **Знания**: 1c-event-sequences, 1c-exchange-protocols, 1c-prometheus-pde, kafka-1c-adapter, 1c-mcp-bsl-context, 1c-ui-design-guide
- **Правила UI**: `.claude/rules/1c/1c-ui-design.md` (элементы форм, компоновка, антипаттерны)
- **MCP**: bsl-context (Синтакс-помощник, Java 17+, 1С 8.3.20+) → `.claude/rules/1c/1c-rules.md`
- Источники: AndreevED/1c-ai-feature-dev-workflow (агенты), Nikolay-Shirokov/cc-1c-skills (67 скиллов)
- Все компоненты связаны кросс-ссылками

## Подробная память
Детали: `.claude/memory/categories/` (tech-stack, preferences, decisions, credentials)
