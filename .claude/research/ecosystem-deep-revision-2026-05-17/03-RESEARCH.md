# Deep Research — 1С AI-ecosystem 2026

> Глубокое исследование инструментов AI-разработки 1С на 2026-05-17.
> Метод: 9 поисковых запросов (WebSearch + WebFetch) + cross-check через 3+ источника на каждое утверждение. deep-researcher agent + 4 точечных WebFetch.

## Метод исследования

Запущен `deep-researcher` agent с заданием:
1. Свежие MCP-серверы для 1С (2026)
2. Альтернативные skill collections
3. AI-инструменты разработки 1С (1С:Напарник, GigaCode, YandexGPT)
4. Развитие BSL Language Server
5. Live database access tools
6. CFE/Extension development tools
7. Сообщество (Infostart 2026, telegram, GitHub trending)

Параллельно выполнены 2 WebSearch'а для уточнения. Затем 4 WebFetch на критичные репозитории.

**Результат:** 25+ инструментов проанализировано, 14 источников.

## Главные находки — топ-5

### 1. feenlace/mcp-1c v1.6.5 ⭐ HIGH PRIORITY

**URL:** https://github.com/feenlace/mcp-1c
**Лицензия:** Open Source (Free) + Pro $25/мес
**Звёзды:** ⭐98 (быстро растущая)
**Обновлено:** 2026-05-15

**Что это:**
MCP-сервер для живой 1С-базы. Go-бинарник, один файл, ноль зависимостей. AI ассистент видит метаданные конфигурации и генерирует точный BSL-код.

**9 tools (все READ-ONLY):**

| Tool | Назначение |
|------|-----------|
| `get_metadata_tree` | Дерево метаданных конфигурации |
| `get_object_structure` | Свойства, реквизиты, табчасти объекта |
| `get_form_structure` | Layout формы + обработчики (XCF парсер с любой глубиной вложенности — новое в v1.6.5) |
| `get_configuration_info` | Свойства конфигурации (имя, версия, поставщик) |
| `search_code` | Полнотекстовый поиск + BM25 + BSL-синонимы |
| `bsl_syntax_help` | Справка по 180+ функциям платформы |
| `execute_query` | Запросы SELECT (write-операции заблокированы) |
| `validate_query` | Проверка синтаксиса запроса |
| `get_event_log` | Чтение журнала регистрации напрямую |

**Чем превосходит наш текущий 1c-transit (MCP Toolkit на 6010):**

| Параметр | 1c-transit | feenlace/mcp-1c v1.6.5 |
|----------|------------|------------------------|
| Безопасность | execute_code (любой код) | Только SELECT, write-операции заблокированы платформой |
| Установка | EPF в толстом клиенте + ручной запуск сервера | Один бинарник `--install` |
| Зависимости | Java + 1C client | Go-бинарь, ноль зависимостей |
| Расширение базы | Не нужно | CFE-расширение (один раз) |
| Журнал регистрации | Через execute_code | Через get_event_log нативно |
| Pro features | Нет | $25/мес: семантический поиск, dependency graphs, аудиты |

**Решение проблемы v1.6.4:**
> "Обновление требует только замены бинарника; расширение 1С переустанавливать не нужно" (release notes v1.6.5)

В нашей памяти `mcp-1c v1.6.4 (требует переустановки расширения)` — это снято в v1.6.5.

**Сложность установки:** низкая. Команды — см. **04-COMMANDS.md**.

### 2. 1c-syntax/claude-code-bsl-lsp ✅ УЖЕ РАБОТАЕТ

**URL:** https://github.com/1c-syntax/claude-code-bsl-lsp
**Лицензия:** Open Source
**Статус у пользователя:** ✅ Установлен через CC plugin marketplace (видно в session boot: "claude-code-bsl-lsp: LSP-сервер BSL Language Server v0.29.0 (130+ диагностик в реальном времени при чтении .bsl)")

**Что это:**
Официальный плагин Claude Code от 1c-syntax для интеграции BSL Language Server через LSP.

**Фичи:**
- Авто-загрузка BSL LS при старте сессии
- 180 диагностик в реальном времени при `Read`/`Edit` файлов .bsl и .os
- Перейти к определению, поиск ссылок, hover info, quick fixes
- Навигация по символам, форматирование
- Авто-обновление каждые 8 минут — всегда свежая версия BSL LS

**Чем превосходит наш ручной `/bsl-lint` скилл:**

| Параметр | `/bsl-lint` skill | claude-code-bsl-lsp |
|----------|-------------------|---------------------|
| Триггер | Явный вызов /bsl-lint | Автоматически при Read/Edit |
| Версия BSL LS | Фиксирована в `tools/bsl-language-server-0.29.0-exec.jar` | Авто-обновляется |
| Скорость | Запуск JVM = ~3-5 сек | Уже работает в памяти |
| Покрытие | Только когда явно вызвано | Каждое чтение/редактирование |

**Команды установки (для информации, у пользователя стоит):**
```bash
claude /plugin marketplace add 1c-syntax/claude-code-bsl-lsp
claude /plugin install bsl-language-server@bsl-language-server
```

### 3. DitriXNew/EDT-MCP v1.31.1 ⏸️ ЗАБЛОКИРОВАНО

**URL:** https://github.com/DitriXNew/EDT-MCP
**Локальная версия:** v1.26.1 (отстаёт на 5 версий)
**Upstream:** v1.31.1

**Что нового в v1.27.0-v1.31.1 (+22 tools, было 34):**

- `get_form_screenshot` — скриншот формы
- `get_form_layout_snapshot` — структурный снимок layout
- `validate_query` — валидация запросов
- `find_references` — поиск ссылок
- 9 семантических групп инструментов
- Management presets

**БЛОКЕР:**
> "v1.27.0+ requires EDT 2026.1+. Earlier versions are not supported."

У пользователя:
- EDT 2025.2.5 (стоит, работает)
- EDT 2026.1 — установка незавершена (см. `memory/edt_2026_1_incomplete_install_2026_05_14.md`: "installations/1C_EDT 2026.1 = огрызок 1.6 MB")

**Что нужно для апгрейда:**
1. Закрыть [edt_2026_1_incomplete_install_2026_05_14.md] — переустановить EDT 2026.1 нормально
2. Мигрировать workspace на EDT 2026.1
3. Обновить EDT-MCP плагин в EDT до v1.31.1

**Риск миграции EDT 2026.1:**
- По MEMORY: "1cedt.exe -data CLI не работает с 2026.1, только Cloud Start UI (▶)"
- Возможна несовместимость с существующим workspace InfoBase5

### 4. 1c-syntax/bsl-language-server v0.30.0-ra.1 ⏳ PRE-RELEASE

**URL:** https://github.com/1c-syntax/bsl-language-server/releases
**Локально:** v0.29.0 stable
**Upstream:** v0.30.0-ra.1 (pre-release, 13.05.2025)

**Что нового в 0.30.0-ra.1:**
- Multi-workspace LSP support с per-workspace configuration
- Семантическая подсветка лямбд внутри string literals
- Исправлены crashes на препроцессорных директивах
- Eclipse LSP4J 0.24.0 → 1.0.0
- ConcurrentHashMap вместо synchronizedMap (производительность)
- `BSLParser` 0.30.0 → 0.32.0
- `MDClasses` 0.17.4 → 0.18.0

**180 диагностик уже сейчас (v0.29.0):**
- Security Hotspot: 8
- Vulnerability: 7
- Error: 56
- Code Smell: 109

**Решение:** подождать stable v0.30.0 (RC может содержать баги). Через `claude-code-bsl-lsp` плагин обновление произойдёт автоматически.

### 5. Arman-Kudaibergenov/1c-ai-development-kit 📚 ДЛЯ ИДЕЙ

**URL:** https://github.com/Arman-Kudaibergenov/1c-ai-development-kit
**Звёзды:** ⭐127
**Версия:** 1.1.0 (post-consolidation)

**Что это:**
Развитие cc-1c-skills (Nikolay-Shirokov) — консолидированная экосистема. Вместо 80 granular skills объединено в 52 + 5 expert-skills с полным охватом функционала.

**Группы (13 skill-групп):**
- Объекты метаданных
- Формы, обработки (EPF), отчёты (ERF)
- СКД, макеты (MXL)
- Роли, подсистемы
- Конфигурация, расширения (CFE)
- Инспекция, валидация
- База данных, веб-клиент, workflow
- **OpenSpec** (proposal/apply/archive)

**Главная фишка — OpenSpec workflow:**
- `openspec-proposal` — создание спецификации
- `openspec-apply` — применение спецификации в код
- `openspec-archive` — архивация выполненных
- 29 спецификаций (XML-форматы объектов)

**Что взять:** идеи OpenSpec → встроить в наш `1c-feature-dev` skill (Phase 0 — Spec)

**Что НЕ делать:** не сливать поверх cc-1c-skills, слишком разные парадигмы.

## Альтернативы существующим — сравнительная таблица

| Текущий инструмент | Альтернатива | Лучше? | Когда менять |
|---|---|---|---|
| METR v0.5.2 (alkoleft) | mcp-onec-test-runner | Нет — это переименование того же | Никогда |
| 1c-transit (MCP Toolkit, port 6010) | **feenlace/mcp-1c v1.6.5** | Дополняет, не заменяет (read-only) | Параллельно |
| cc-1c-skills (Nikolay-Shirokov, 66 skills, ⭐312) | Arman-Kudaibergenov/1c-ai-development-kit (52 skills, ⭐127) | Спорно — у Arman OpenSpec, у Nikolay больше CLI-абстракций | Не менять, взять идеи |
| comol/ai_rules_1c (28 файлов, ⭐251) | 1c-buddy + spring-mcp-1c-copilot (1С:Напарник) | Нет — comol самый полный rules-набор | Не менять |
| mcp-bsl-context v0.3.2 (alkoleft) | alkoleft/bsl-graph (NebulaGraph) | Не сравнимо — bsl-graph в alpha | Подождать stable |
| `/bsl-lint` skill (ручной) | claude-code-bsl-lsp плагин | Да — авто-инкорпорированный | Уже работает ✅ |

## НЕ рекомендую (с обоснованием)

### 1С:Напарник (от Yandex/Sber)

**Что:** Внутренний AI-ассистент для EDT, ИТС-интеграция.

**Почему НЕ:**
- Только EDT 2023.3.6+ (закрытая среда)
- Нет публичного API
- Не интегрируется с Claude Code
- Бесплатно только до окт.2026 по ИТС (после — неясно)
- Закрытая экосистема, vendor lock-in

### alkoleft/bsl-graph

**Что:** Анализатор+визуализатор кода 1С в NebulaGraph, REST API + MCP.

**Почему НЕ:**
- Alpha-стадия
- "4 commits на master", без релизов
- Требует NebulaGraph (тяжёлый dep)
- Цель та же что у `mcp-bsl-context`, но не стабилен

### infaton/MCP35

**Что:** 51 tool для ERP, MCP-сервер с full CRUD-правами.

**Почему НЕ:**
- CRUD-операции на боевую базу — опасно
- Без ревью кода — рисков много
- Заявлено 35 tool, по факту 51 (несоответствие документации)
- Для песочниц только

### hawkxtreme/mini-ai-1c v1.2.7

**Что:** Tauri+React десктоп ассистент.

**Почему НЕ:**
- Дублирует функционал Claude Code + Конфигуратор
- 203⭐ но **39 open issues** — нестабилен
- Свой UI вместо использования CC
- Tauri зависимости

### YandexGPT для 1С

**Что:** Yandex Code Assistant для BSL.

**Почему НЕ:**
- По тестам слабый: "перечисляет имена папок без анализа"
- Хуже Claude 4.x по качеству генерации BSL
- Локальная Russia-only альтернатива без преимуществ

### Infostart MCP (платный marketplace 2460659)

**Что:** Закрытый платный MCP-каталог.

**Почему НЕ:**
- Нет открытого кода
- Vendor lock-in
- Риски безопасности высокие

## Новинки сообщества Infostart 2026 (на заметке)

### Code Index (Infostart 2677918)

**Что:** Структурный поиск по выгрузке кода 1С через MCP.

**Применимость:** альтернатива/дополнение к `mcp-bsl-context.search`.

**Статус:** на заметке, не пробовать пока нет PoC.

### Claude Note (Infostart 2659511)

**Что:** Превращение сессий Claude Code в структурированные знания.

**Применимость:** memory/knowledge management. У нас есть свой `memory-management` skill — возможно идеи.

### PromptPilot (Infostart 2653416)

**Что:** Task manager для Claude Code и Codex.

**Применимость:** альтернатива TaskCreate/TaskList. Спорно.

### Infostart 2605838 — "Вайб-кодинг с MCP"

**Что:** Практический разбор AI-разработки 1С через MCP-серверы.

**Ключевое утверждение:** **44% AI-генерированного кода требует ручного исправления.** Подтверждает наше правило 3 итераций Матакова (`rules/1c/1c-ai-collaboration.md`).

### Infostart 2650687 — "Бесплатное выполнение CC"

**Что:** Claude Code Router, agentrouter — альтернативы для оптимизации стоимости.

**Применимость:** на заметке для cost-optimization.

## Карта 40+ MCP-серверов для 1С

**Источник:** github.com/Untru/1c-mcp

| Категория | Серверы |
|-----------|---------|
| **IDE интеграции** | EDT-MCP, CodePilot1C, 1C: Platform Tools MCP |
| **Frameworks** | 1c_mcp (vladimir-kharin), 1c-mcp-toolkit, http1c |
| **Metadata & Code Analysis** | feenlace/mcp-1c, 1c-mcp-metacode, bsl-graph (alpha) |
| **Platform docs** | mcp-bsl-platform-context, onec-help-mcp |
| **Testing & Validation** | bsl-mcp, mcp-onec-test-runner (METR) |
| **Business Integration** | 1c-rest-mcp, ARQA MCP Server (платный) |

**Самые активные и стабильные (по аудиту deep-researcher):**
1. mcp-bsl-context (alkoleft) — справка платформы ✅
2. mcp-onec-test-runner / METR (alkoleft) — тестирование ✅
3. feenlace/mcp-1c — живая база, RO ⭐ (рекомендация)
4. EDT-MCP — IDE plugin (заблокировано EDT)
5. cursor_rules_1c — комплексный AI ruleset

## Развитие активных проектов 2026

### alkoleft (3 проекта)

- **mcp-bsl-context** — стабилен на v0.3.2, добавили SSE/HTTP режим в дополнение к STDIO
- **METR** (mcp-onec-test-runner) — стабилен v0.5.2 (март 2026)
- **bsl-graph** — НОВЫЙ: NebulaGraph анализатор, REST API + MCP. Alpha, рано

### 1c-syntax

- BSL LS v0.30.0-ra.1 в RC; миграция на JDK 21
- **claude-code-bsl-lsp** — официальный путь интеграции CC ✅

### comol/ai_rules_1c (⭐251)

- Активная разработка (commits 14-17 мая 2026)
- Расширение под 6 IDE (Cursor / Claude Code / Codex / OpenCode / Kilo / другие)
- Telegram-канал, платформа vibecoding1c.ru
- Pivot к OpenSpec в качестве workflow

### DitriXNew

- EDT-MCP v1.31.1 — крупное обновление (+22 tools, было 34)
- Требует EDT 2026.1+

## Сводка приоритетов

### 🔴 HIGH PRIORITY

1. **feenlace/mcp-1c v1.6.5** — read-only MCP для боевой базы. Бинарь скачан, осталось установить расширение и добавить в .mcp.json. См. **04-COMMANDS.md**.

### 🟡 MEDIUM PRIORITY

2. **EDT-MCP v1.31.1** — заблокировано EDT 2025.2. Если активировать EDT 2026.1 — мощный апгрейд (+22 tools).
3. **Arman-Kudaibergenov OpenSpec идеи** — встроить в наш `1c-feature-dev` Phase 0.
4. **Code Index, Claude Note** — попробовать когда найдётся время.

### 🔵 LOW PRIORITY

5. **BSL LS v0.30.0 stable** — подождать релиз (через claude-code-bsl-lsp апдейт авто).
6. **Untru/1c-mcp каталог** — справочник при подборе MCP под задачу.

### ❌ ОТКЛОНЕНО

7. ECC массовый refresh — context bloat, ничего критически нужного.
8. 1С:Напарник — закрытая среда.
9. alkoleft/bsl-graph — alpha.
10. infaton/MCP35, hawkxtreme/mini-ai-1c, YandexGPT — низкое качество или риски.

## Источники (verified 2026-05-17)

### MCP-серверы
- [feenlace/mcp-1c](https://github.com/feenlace/mcp-1c) — read-only MCP v1.6.5
- [DitriXNew/EDT-MCP](https://github.com/DitriXNew/EDT-MCP) — EDT plugin v1.31.1
- [alkoleft/mcp-onec-test-runner](https://github.com/alkoleft/mcp-onec-test-runner) — METR
- [alkoleft/mcp-bsl-platform-context](https://github.com/alkoleft/mcp-bsl-platform-context) — справка платформы
- [alkoleft/bsl-graph](https://github.com/alkoleft/bsl-graph) — alpha анализатор
- [vladimir-kharin/1c_mcp](https://github.com/vladimir-kharin/1c_mcp) — live database access
- [yellow-hammer/mcp-1c-platform-tools](https://github.com/yellow-hammer/mcp-1c-platform-tools) — VS Code IPC

### Catalogs and Lists
- [Untru/1c-mcp](https://github.com/Untru/1c-mcp) — каталог 40+ MCP

### BSL Tooling
- [1c-syntax/bsl-language-server](https://github.com/1c-syntax/bsl-language-server) — BSL LS releases
- [1c-syntax/claude-code-bsl-lsp](https://github.com/1c-syntax/claude-code-bsl-lsp) — официальный CC plugin
- [BSL LS diagnostics docs](https://1c-syntax.github.io/bsl-language-server/en/diagnostics/) — 180 правил

### Skill Collections
- [Nikolay-Shirokov/cc-1c-skills](https://github.com/Nikolay-Shirokov/cc-1c-skills) — 66 skills ⭐312
- [Arman-Kudaibergenov/1c-ai-development-kit](https://github.com/Arman-Kudaibergenov/1c-ai-development-kit) — 52 skills + OpenSpec ⭐127
- [comol/ai_rules_1c](https://github.com/comol/ai_rules_1c) — rules+skills для 6 IDE ⭐251

### Не рекомендую
- [infaton/MCP35](https://github.com/infaton/MCP35) — 51 tool с CRUD ❌
- [hawkxtreme/mini-ai-1c](https://github.com/hawkxtreme/mini-ai-1c) — Tauri десктоп ❌
- [1С:Напарник](https://code.1c.ai/) — закрытая EDT-only ❌

### Сообщество Infostart
- [Infostart 2605838 — Вайб-кодинг с MCP](https://infostart.ru/1c/articles/2605838/)
- [Infostart 2650687 — Бесплатное выполнение CC](https://infostart.ru/1c/articles/2650687/)
- [Infostart 2677918 — Code Index](https://infostart.ru/1c/articles/2677918/)
- [Infostart 2659511 — Claude Note](https://infostart.ru/1c/articles/2659511/)
- [Infostart 2653416 — PromptPilot](https://infostart.ru/1c/articles/2653416/)

### Практика
- [Денис Матаков — Claude Code и 1С:Предприятие](https://matakov.com/claude-code-i-1s-predpriyatie/)
