# Бэклог — Задачи на будущее

> Список инструментов, идей и задач для установки/интеграции.
> Обновляется по мере обнаружения интересных проектов.

---

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

### 3. METR — MCP Test Runner для 1С
- **Репо:** https://github.com/alkoleft/mcp-onec-test-runner
- **Что:** MCP-сервер для запуска YaXUnit тестов, сборки проектов и проверки синтаксиса через AI
- **Зачем:** Автотесты из Claude Code -> написал код -> запустил тесты -> получил результат. Усилит Phase 7 в 1c-feature-dev
- **Стек:** Kotlin, JDK 17+, 1С 8.3.10+, YaXUnit, 76 звёзд, GPL-3.0
- **Приоритет:** 🟡 Средний (нужен YaXUnit в проекте)
- **Статус:** ⏳ Ожидает

### 4. 1c_mcp — MCP-сервер для доступа к живой базе 1С
- **Репо:** https://github.com/vladimir-kharin/1c_mcp
- **Что:** MCP-сервер на платформе 1С — даёт AI прямой доступ к данным, метаданным и бизнес-логике живой базы
- **Фишка:** CFE-расширение + Python-прокси (OAuth2, stdio transport). AI автономно запрашивает нужные данные через tools/resources/prompts
- **Зачем:** Дополняет bsl-context (синтаксис) и MCP RAQ (поиск метаданных) — этот даёт доступ к реальным данным базы
- **Стек:** 1C Enterprise + Python, 296 звёзд, MIT
- **Приоритет:** 🟡 Средний (нужна опубликованная база с HTTP-сервисом)
- **Статус:** ⏳ Ожидает

### 5. mcp-bsl-platform-context v0.3.2 — Обновление синтакс-помощника 1С
- **Репо:** https://github.com/alkoleft/mcp-bsl-platform-context
- **Что:** MCP-сервер для проверки синтаксиса 1С (search, info, getMember, getMembers, getConstructors)
- **Текущая версия:** v0.3.0 (сконфигурирован в bsl-context через Java)
- **Новое в v0.3.2:** улучшенный поиск, дополнительные методы платформы
- **Обновление:** скачать новый JAR с https://github.com/alkoleft/mcp-bsl-platform-context/releases/latest, заменить путь в `.claude/settings.json` → bsl-context
- **Приоритет:** 🟡 Средний (обновить при следующей 1С-сессии)
- **Статус:** ⏳ Ожидает (нужно скачать JAR вручную)

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
