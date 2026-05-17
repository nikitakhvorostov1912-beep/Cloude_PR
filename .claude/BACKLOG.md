# Бэклог — Задачи на будущее

> Список инструментов, идей и задач для установки/интеграции.
> Обновляется по мере обнаружения интересных проектов.

---

## Связанные документы

- **`.claude/research/ecosystem-deep-revision-2026-05-17/`** — полный отчёт ревизии экосистемы (2026-05-17, 6 файлов, 116 KB). README.md — навигация. См. `05-ROADMAP.md` для приоритетов P0/P1/P2/P3.

## К установке / интеграции

### 1. AIChat — Универсальный CLI для LLM
- **Репо:** https://github.com/sigoden/aichat
- **Что:** Единый CLI для 20+ LLM-провайдеров (OpenAI, Claude, Gemini, Ollama, Deepseek и др.)
- **Зачем:** Shell Assistant (NL->команды), локальный OpenAI-совместимый прокси (`aichat --serve`), RAG из коробки, MCP поддержка, LLM Arena
- **Установка:** `cargo install aichat` / `scoop install aichat` (Windows)
- **Приоритет:** 🟡 Средний
- **Статус:** ⏳ Ожидает

### 2. BSL Atlas — Семантический поиск по коду 1С
- **Репо:** https://github.com/Arman-Kudaibergenov/bsl-atlas
- **Что:** MCP-сервер: векторный поиск, структурный индекс и граф вызовов по коду конфигурации 1С
- **Фишка:** Два режима — быстрый (SQLite) и полный (ChromaDB + embeddings). Поиск по описанию: "как реализовано проведение"
- **Зачем:** Дополняет bsl-context (API платформы) анализом кода конфигурации. Подключать когда появится реальная конфигурация для анализа
- **Стек:** Python, SQLite, ChromaDB, Qwen3 embeddings, 37 звёзд, MIT
- **Приоритет:** 🟡 Средний (нужна реальная конфигурация)
- **Статус:** ⏳ Ожидает

### 3. METR — MCP Test Runner для 1С ✅ УСТАНОВЛЕНО
- **Репо:** https://github.com/alkoleft/mcp-onec-test-runner
- **Что:** MCP-сервер для запуска YaXUnit тестов, сборки проектов и проверки синтаксиса через AI
- **Зачем:** Автотесты из Claude Code -> написал код -> запустил тесты -> получил результат. Усилит Phase 7 в 1c-feature-dev
- **Стек:** Kotlin, JDK 17+, 1С 8.3.10+, YaXUnit, 76 звёзд, GPL-3.0
- **Приоритет:** 🟡 Средний (нужен YaXUnit в проекте)
- **Статус:** ✅ v0.5.2 (последняя), JAR в `tools/mcp-onec-test-runner.jar`, config — `application-metr-v2.yml`

### 4. 1c_mcp — MCP-сервер для доступа к живой базе 1С
- **Репо:** https://github.com/vladimir-kharin/1c_mcp
- **Что:** MCP-сервер на платформе 1С — даёт AI прямой доступ к данным, метаданным и бизнес-логике живой базы
- **Фишка:** CFE-расширение + Python-прокси (OAuth2, stdio transport). AI автономно запрашивает нужные данные через tools/resources/prompts
- **Зачем:** Дополняет bsl-context (синтаксис) и MCP RAQ (поиск метаданных) — этот даёт доступ к реальным данным базы
- **Стек:** 1C Enterprise + Python, 296 звёзд, MIT
- **Приоритет:** 🟡 Средний (нужна опубликованная база с HTTP-сервисом)
- **Статус:** ⏳ Ожидает (заменён в roadmap на feenlace/mcp-1c v1.6.5 — см. ниже)

### 4.1. feenlace/mcp-1c v1.6.5 — Read-only MCP для живой базы ⭐ HIGH PRIORITY
- **Репо:** https://github.com/feenlace/mcp-1c
- **Что:** Go-бинарник, MCP-сервер для живой 1С базы. 9 tools: метадерево, структура объектов/форм, search_code (BM25+BSL-синонимы), bsl_syntax_help (180 функций), execute_query (SELECT only), validate_query, get_event_log
- **Чем превосходит 1c-transit:** READ-ONLY (только SELECT, никаких write-операций — безопаснее для боевой базы); Go-бинарь, ноль зависимостей; один установщик `mcp-1c --install`
- **Версия 1.6.5 (2026-05-15):** новый парсер форм XCF (любая глубина вложенности + обработчики событий). НЕ требует переустановки расширения при обновлении (решено в v1.6.5)
- **Pro $25/мес:** семантический поиск, dependency graphs, аудиты — НЕ обязательно
- **Стек:** Go, ⭐98, активная разработка
- **Бинарь:** скачан в `C:/CLOUDE_PR/tools/mcp-1c-windows-amd64.v1.6.5.exe`
- **Установка:** `mcp-1c-windows-amd64.v1.6.5.exe --install "Srvr=is-srv1c-02:5541;Ref=ut_rt_copy" --server --db-user Администратор --db-password 123`, затем добавить в `.mcp.json`
- **Приоритет:** 🔴 ВЫСОКИЙ
- **Статус:** ⏳ Бинарь скачан, расширение НЕ установлено

### 4.2. Arman-Kudaibergenov/1c-ai-development-kit — Альтернатива cc-1c-skills
- **Репо:** https://github.com/Arman-Kudaibergenov/1c-ai-development-kit
- **Что:** Консолидированная экосистема на 52 skills (вместо 80 granular у cc-1c-skills) + 29 спецификаций + 13 skill-групп
- **Фишка:** OpenSpec workflow (openspec-proposal/apply/archive), Cursor agents, ребрендинг 5 expert-skills с полным охватом
- **Развилось из:** cc-1c-skills от Nikolay-Shirokov
- **Зачем смотреть:** не для миграции, для идей. OpenSpec может зайти в наш `1c-feature-dev`
- **Приоритет:** 🟡 Средний (изучить идеи, не сливать)
- **Статус:** ⏳ На заметке

### 4.3. 1c-syntax/claude-code-bsl-lsp — Официальный Claude Code плагин для BSL LS ✅ УСТАНОВЛЕНО
- **Репо:** https://github.com/1c-syntax/claude-code-bsl-lsp
- **Что:** Официальный плагин Claude Code от 1c-syntax. Авто-загрузка BSL LS, 180+ диагностик в реальном времени при чтении .bsl, авто-обновление каждые 8 минут
- **Чем превосходит ручной /bsl-lint skill:** работает автоматически при Read/Edit, не нужно явно вызывать; всегда свежая версия BSL LS
- **Команды установки:**
  ```
  claude /plugin marketplace add 1c-syntax/claude-code-bsl-lsp
  claude /plugin install bsl-language-server@bsl-language-server
  ```
- **Статус:** ✅ Уже работает (видно в session boot — v0.29.0 active, 130+ диагностик)

### 4.4. Untru/1c-mcp — Каталог 40+ MCP-серверов для 1С
- **Репо:** https://github.com/Untru/1c-mcp
- **Что:** Куратированный каталог MCP-серверов для экосистемы 1С:Предприятие
- **Группы:** IDE интеграции (EDT-MCP, CodePilot1C, 1C: Platform Tools MCP), Frameworks (1c_mcp, 1c-mcp-toolkit, http1c), Metadata & Code Analysis (mcp-1c, 1c-mcp-metacode, bsl-graph), Platform Docs (mcp-bsl-platform-context, onec-help-mcp), Testing (bsl-mcp, METR), Business (1c-rest-mcp, ARQA)
- **Зачем:** справочник при подборе MCP под задачу
- **Приоритет:** 🔵 Низкий (просто карта)
- **Статус:** ⏳ На заметке

### 4.5. EDT-MCP v1.31.1 — апгрейд EDT-MCP плагина ⏸️ ЗАБЛОКИРОВАНО
- **Репо:** https://github.com/DitriXNew/EDT-MCP
- **Текущая версия:** v1.26.1 (стоит в EDT 2025.2.5)
- **Upstream:** v1.31.1 — +22 tools (get_form_screenshot, get_form_layout_snapshot, validate_query, find_references, 9 семантических групп, management presets)
- **БЛОКЕР:** v1.27.0+ требует EDT 2026.1+. У пользователя EDT 2025.2.5 + EDT 2026.1 недоустановлена (см. memory/edt_2026_1_incomplete_install_2026_05_14.md)
- **Действие:** доустановить EDT 2026.1 → апгрейд EDT-MCP до 1.31.1
- **Приоритет:** 🟡 Средний (после установки EDT 2026.1)
- **Статус:** ⏸️ Заблокировано установкой EDT 2026.1

### 5. mcp-bsl-platform-context — Обновление синтакс-помощника 1С ✅ УСТАНОВЛЕНО
- **Репо:** https://github.com/alkoleft/mcp-bsl-platform-context
- **Что:** MCP-сервер для проверки синтаксиса 1С (search, info, getMember, getMembers, getConstructors)
- **Текущая версия:** v0.3.2 (актуальная, JAR в `tools/mcp-bsl-context-0.3.2.jar`)
- **Статус:** ✅ Подключён в `.mcp.json` как `bsl-context`

### 6. AndreevED/1c-ai-feature-dev-workflow — Методология AI-разработки 1С
- **Репо:** https://github.com/AndreevED/1c-ai-feature-dev-workflow
- **Что:** Методология и промпты для AI-assisted разработки 1С — практический опыт с примерами
- **Зачем:** Обновить скилл `1c-feature-dev` на основе реального опыта сообщества
- **Приоритет:** 🟡 Средний (прочитать и взять лучшие практики)
- **Статус:** ⏳ На заметке

### 7. Claude Context MCP — Семантический поиск по кодовой базе
- **Репо:** https://github.com/zilliztech/claude-context
- **Что:** MCP-плагин, добавляющий семантический поиск по всему репозиторию — гибридный поиск, AST-чанкинг, инкрементальная индексация
- **Установка:** `claude mcp add claude-context` (через Claude CLI)
- **Требования:** Zilliz Cloud API key (или Milvus локально), embedding provider (OpenAI/Ollama/Gemini)
- **Зачем:** Глубокий контекст при работе с большими кодовыми базами (1С конфигурации, MOEX project)
- **Стек:** TypeScript, Milvus, VSCode extension, MIT
- **Приоритет:** 🟡 Средний (нужен Zilliz API key или Milvus)
- **Статус:** ⏳ На заметке

### 8. Unity MCP — AI-мост к Unity Editor
- **Репо:** https://github.com/CoplayDev/unity-mcp
- **Что:** MCP-сервер для управления Unity Editor через Claude/Cursor. 30+ инструментов, 6.7k звёзд
- **Зачем:** AI-управление сценами, ассетами, скриптами Unity через натуральный язык
- **Приоритет:** 🔵 Низкий (пока не нужен)
- **Статус:** На заметке

### 9. OpenIntegrations — Библиотека интеграций 1С с 30+ сервисами
- **Репо:** https://github.com/Bayselonarrend/OpenIntegrations
- **Что:** Готовые методы интеграции 1С с Telegram, Bitrix24, Google, Yandex, PostgreSQL, S3, Slack, Notion, Airtable и др.
- **Формат:** CFE-расширение, OneScript-пакет, CLI (Windows/Linux)
- **Стек:** 1C Enterprise, 560 звёзд, MIT, v1.33.0 (март 2026)
- **Зачем:** Справочник готовых методов при задачах на интеграцию 1С с внешними API
- **Приоритет:** 🔵 Низкий (подключать когда появится задача на интеграцию)
- **Статус:** На заметке

### 10. Parry — Сканер prompt injection для хуков Claude Code
- **Источник:** https://github.com/hesreallyhim/awesome-claude-code
- **Что:** Инструмент для обнаружения prompt injection атак в tool inputs/outputs хуков Claude Code
- **Зачем:** Безопасность при работе с внешними данными (API ответы, файлы пользователей)
- **Приоритет:** 🟡 Средний (безопасность)
- **Статус:** ⏳ На заметке

---

## Установленные

| # | Инструмент | Путь / Версия | Примечание |
|---|-----------|---------------|------------|
| 1 | Xonsh | v0.22.6 | Python-powered shell |
| 2 | E2B Fragments | `tools/fragments/` | Нужен E2B_API_KEY |
| 3 | Awesome Subagents | `tools/awesome-subagents/` | 6 из 103 агентов установлены |
| 4 | Marketing Skills | `.claude/skills/marketing/` | 33 скилла |
| 5 | Claude Monitor | v3.1.0 (`ccm`) | Мониторинг использования |
| 6 | MCP RAQ 1C | `tools/mcp-raq-1c/` | Docker Desktop + XML-выгрузка |
| 7 | Pake CLI | v3.10.0 | Desktop-обёртки для веба |
| 8 | ECC | `.claude/{agents,skills,commands}/ecc/` | 16 агентов, 94 скилла, 48 команд |
| 9 | Composio MCP | plugin | 500+ SaaS-интеграций |
| 10 | n8n-MCP | `.mcp.json` | 1239 нод автоматизации, docs-only без N8N_API_URL |

---

## Выполненные задачи

- [x] Deep Researcher агент (deep-researcher + research-fetcher)
- [x] Code Scout, Code Reviewer, Bug Hunter агенты
- [x] Хуки (Stop, SubagentStop)
- [x] Composio MCP интеграция
- [x] UI/UX Pro Max обновление
- [x] Everything Claude Code (ECC) интеграция
- [x] Memory Management скилл (3-уровневая иерархия)
- [x] PreCompact хук (резервная копия STATE.md перед компрессией контекста)
- [x] pr-review-toolkit плагин (6 агентов ревью + /review-pr команда)
- [x] isolation:worktree для bug-hunter и rapid-prototyper
- [x] MCP серверы: sequential-thinking, memory, fetch (`.mcp.json`)
- [x] parallel-executor агент (Fan-Out/Fan-In, MapReduce, Multi-Perspective, Speculative)
- [x] contextual-rag скилл (5 паттернов RAG, LanceDB, GraphRAG)
- [x] cost-optimization скилл (маршрутизация Haiku/Sonnet/Opus, Prompt Caching, Batch API)
- [x] 5 агентов из rohitg00/awesome-claude-code-toolkit: mlops-engineer, vector-database-engineer, documentation-engineer, kubernetes-specialist, terraform-engineer
- [x] Obsidian vault синхронизация (Junction Point + MCP mcpvault)
- [x] qa-automation агент (rohitg00 toolkit) — 2026-03-23
- [x] security-researcher агент (rohitg00 toolkit) — 2026-03-23
- [x] n8n-mcp сервер добавлен в .mcp.json — 2026-03-23
- [x] financial-analyst агент (custom, для MOEX trading) — 2026-03-23
- [x] 1c-data-analyst агент (из раздела Ideas BACKLOG) — 2026-03-23

---

## Идеи

### 1c-data-analyst — ✅ РЕАЛИЗОВАН (2026-03-23)
Агент создан: `.claude/agents/1c-data-analyst.md`

### Obsidian Vault: 1С Analyst Workspace
- **Что:** Экосистема знаний аналитика 1С в Obsidian (14 зон, 27 заметок, ~170 связей)
- **Roadmap:** `1С Экосистема/12 — Развитие/Развитие — Индекс.md`
- **Текущая фаза:** Фаза 2 — Ядро знаний (~60%)
- **Следующий шаг:** дозаполнить Фазу 2 (процессы, БСП, запросы), установить Dataview
- **Статус:** В работе

---

*Последнее обновление: 2026-03-23*
