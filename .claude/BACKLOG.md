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
- **Приоритет:** Средний
- **Статус:** Ожидает

### 2. BSL Atlas — Семантический поиск по коду 1С
- **Репо:** https://github.com/Arman-Kudaibergenov/bsl-atlas
- **Что:** MCP-сервер: векторный поиск, структурный индекс и граф вызовов по коду конфигурации 1С
- **Фишка:** Два режима — быстрый (SQLite) и полный (ChromaDB + embeddings). Поиск по описанию: "как реализовано проведение"
- **Зачем:** Дополняет bsl-context (API платформы) анализом кода конфигурации. Подключать когда появится реальная конфигурация для анализа
- **Стек:** Python, SQLite, ChromaDB, Qwen3 embeddings, 37 звёзд, MIT
- **Приоритет:** Средний (нужна реальная конфигурация)
- **Статус:** Ожидает

### 3. METR — MCP Test Runner для 1С
- **Репо:** https://github.com/alkoleft/mcp-onec-test-runner
- **Что:** MCP-сервер для запуска YaXUnit тестов, сборки проектов и проверки синтаксиса через AI
- **Зачем:** Автотесты из Claude Code -> написал код -> запустил тесты -> получил результат. Усилит Phase 7 в 1c-feature-dev
- **Стек:** Kotlin, JDK 17+, 1С 8.3.10+, YaXUnit, 76 звёзд, GPL-3.0
- **Приоритет:** Средний (нужен YaXUnit в проекте)
- **Статус:** Ожидает

### 4. 1c_mcp — MCP-сервер для доступа к живой базе 1С
- **Репо:** https://github.com/vladimir-kharin/1c_mcp
- **Что:** MCP-сервер на платформе 1С — даёт AI прямой доступ к данным, метаданным и бизнес-логике живой базы
- **Фишка:** CFE-расширение + Python-прокси (OAuth2, stdio transport). AI автономно запрашивает нужные данные через tools/resources/prompts
- **Зачем:** Дополняет bsl-context (синтаксис) и MCP RAQ (поиск метаданных) — этот даёт доступ к реальным данным базы
- **Стек:** 1C Enterprise + Python, 296 звёзд, MIT
- **Приоритет:** Средний (нужна опубликованная база с HTTP-сервисом)
- **Статус:** Ожидает

### 5. Unity MCP — AI-мост к Unity Editor
- **Репо:** https://github.com/CoplayDev/unity-mcp
- **Что:** MCP-сервер для управления Unity Editor через Claude/Cursor. 30+ инструментов, 6.7k звёзд
- **Зачем:** AI-управление сценами, ассетами, скриптами Unity через натуральный язык
- **Приоритет:** Низкий (пока не нужен)
- **Статус:** На заметке

### 6. Claude Scientific Skills — 170+ научных скиллов
- **Репо:** https://github.com/K-Dense-AI/claude-scientific-skills
- **Что:** 170 скиллов для научных исследований, 250+ баз данных, 60+ Python-пакетов
- **Домены:** биоинформатика, хеминформатика, drug discovery, медицинская визуализация, физика, астрономия
- **Приоритет:** Низкий (нишевый научный проект)
- **Статус:** На заметке

### 7. AI Research Skills — 85 скиллов для AI/ML research
- **Репо:** https://github.com/Orchestra-Research/AI-Research-SKILLs
- **Что:** 85 скиллов в 21 категории: архитектуры моделей, fine-tuning, distributed training, inference, RAG, MLOps, safety
- **Установка:** `npx @orchestra-research/ai-research-skills`
- **Приоритет:** Низкий (нужен когда начнётся ML/AI проект)
- **Статус:** На заметке

### 8. Casibase — Open-source AI Cloud OS
- **Репо:** https://github.com/casibase/casibase
- **Что:** AI-платформа с RAG knowledge base, SSO, 20+ LLM, MCP/A2A координация, speech/vision
- **Стек:** Go + React + MySQL + Docker/K8s, 4.5k звёзд
- **Приоритет:** Низкий (enterprise-платформа, overkill для текущих задач)
- **Статус:** На заметке

### 9. Serena — Semantic Code Navigation MCP
- **Репо:** https://github.com/oraios/serena
- **Что:** MCP-сервер для символьной навигации по коду через LSP (30+ языков)
- **Фишка:** `find_symbol`, `insert_after_symbol` вместо файловых операций — экономит токены на крупных кодовых базах
- **Стек:** Python, LSP, MCP SDK, JetBrains plugin
- **Приоритет:** Низкий (вернуться если будут проблемы с навигацией по большим проектам)
- **Статус:** На заметке

### 10. OpenIntegrations — Библиотека интеграций 1С с 30+ сервисами
- **Репо:** https://github.com/Bayselonarrend/OpenIntegrations
- **Что:** Готовые методы интеграции 1С с Telegram, Bitrix24, Google, Yandex, PostgreSQL, S3, Slack, Notion, Airtable и др.
- **Формат:** CFE-расширение, OneScript-пакет, CLI (Windows/Linux)
- **Стек:** 1C Enterprise, 560 звёзд, MIT, v1.33.0 (март 2026)
- **Зачем:** Справочник готовых методов при задачах на интеграцию 1С с внешними API
<<<<<<< Updated upstream
- **Приоритет:** 🔵 Низкий (подключать когда появится задача на интеграцию)
- **Статус:** ⏳ На заметке

### ~~14. MCP RAQ 1C — RAG-поиск по метаданным конфигурации~~ ✅ Установлен
- **Репо:** https://github.com/Antiloop-git/MCP-RAQ-1C
- **Путь:** `tools/mcp-raq-1c/`
- **Запуск:** `tools/mcp-raq-1c/start.bat` (5 Docker-контейнеров), MCP endpoint: `http://localhost:8000/sse`
- **Бонус:** скилл `1c-queries` скопирован в `.claude/skills/` (запросы к базе 1С через HTTP-сервис)
- **Статус:** ✅ Установлен (требует Docker Desktop + XML-выгрузку конфигурации для индексации)

### 17. mcp-bsl-platform-context v0.3.2 — Обновление синтакс-помощника 1С
- **Репо:** https://github.com/alkoleft/mcp-bsl-platform-context
- **Что:** MCP-сервер для проверки синтаксиса 1С (search, info, getMember, getMembers, getConstructors)
- **Текущая версия:** v0.3.0 (сконфигурирован в bsl-context через Java)
- **Новое в v0.3.2:** улучшенный поиск, дополнительные методы платформы
- **Обновление:** скачать новый JAR с https://github.com/alkoleft/mcp-bsl-platform-context/releases/latest, заменить путь в `.claude/settings.json` → bsl-context
- **Приоритет:** 🟡 Средний (обновить при следующей 1С-сессии)
- **Статус:** ⏳ Ожидает (нужно скачать JAR)

### 18. EDT-MCP — MCP-сервер для работы с EDT (1C:Enterprise Development Tools)
- **Репо:** https://github.com/nikonov-alex/edt-mcp (или аналог)
- **Что:** MCP-сервер для интеграции с EDT 2025.2+ — компиляция, валидация, анализ кода прямо из Claude Code
- **Требования:** EDT 2025.2+, Java 17+
- **Зачем:** Более точная валидация чем через скрипты — EDT знает всё о конфигурации
- **Приоритет:** 🔵 Низкий (требует EDT 2025.2+ установленный)
- **Статус:** ⏳ На заметке (условно — когда будет EDT)

### 19. AndreevED/1c-ai-feature-dev-workflow — Методология AI-разработки 1С
- **Репо:** https://github.com/AndreevED/1c-ai-feature-dev-workflow
- **Что:** Методология и промпты для AI-assisted разработки 1С — практический опыт с примерами
- **Зачем:** Обновить скилл `1c-feature-dev` на основе реального опыта сообщества
- **Приоритет:** 🟡 Средний (прочитать и взять лучшие практики)
- **Статус:** ⏳ На заметке

### 20. Arman-Kudaibergenov/1c-ai-development-kit — Набор AI-инструментов 1С
- **Репо:** https://github.com/Arman-Kudaibergenov/1c-ai-development-kit
- **Что:** Полный набор: промпты, агенты, правила для AI-разработки 1С
- **Зачем:** Дополнить текущую 1С-экосистему новыми паттернами
- **Приоритет:** 🟡 Средний (изучить после AndreevED)
- **Статус:** ⏳ На заметке

### ~~5. Awesome Claude Code Subagents~~ ✅ Проанализированы
- **Репо:** https://github.com/VoltAgent/awesome-claude-code-subagents
- **Что:** 103 агента в 10 категориях
- **Путь:** `tools/awesome-subagents/`
- **Установлено 6 агентов:** performance-engineer, api-designer, docker-expert, mcp-developer, devops-engineer, prompt-engineer
- **Статус:** ✅ Лучшие установлены, наши агенты оказались лучше в дублях (code-reviewer, bug-hunter)

### ~~6. Marketing Skills~~ ✅ Установлены
- **Репо:** https://github.com/coreyhaines31/marketingskills
- **Путь:** `.claude/skills/marketing/`
- **Что:** 32 маркетинговых скилла (SEO, CRO, copywriting, ads, email и др.)
- **Статус:** ✅ Установлены

### ~~7. Claude Code Usage Monitor~~ ✅ Установлен
- **Репо:** https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor
- **Версия:** v3.1.0 (`claude-monitor` / `ccm`)
- **Статус:** ✅ Установлен
=======
- **Приоритет:** Низкий (подключать когда появится задача на интеграцию)
- **Статус:** На заметке
>>>>>>> Stashed changes

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

---

## Выполненные задачи

- [x] Deep Researcher агент (deep-researcher + research-fetcher)
- [x] Code Scout, Code Reviewer, Bug Hunter агенты
- [x] Хуки (Stop, SubagentStop)
- [x] Composio MCP интеграция
- [x] UI/UX Pro Max обновление
- [x] Everything Claude Code (ECC) интеграция
- [x] Memory Management скилл (3-уровневая иерархия)
<<<<<<< Updated upstream
- [x] PreCompact хук (резервная копия STATE.md перед компрессией контекста)
- [x] pr-review-toolkit плагин (6 агентов ревью + /review-pr команда)
- [x] isolation:worktree для bug-hunter и rapid-prototyper
- [x] MCP серверы: sequential-thinking, memory, fetch (`.mcp.json`)
- [x] parallel-executor агент (Fan-Out/Fan-In, MapReduce, Multi-Perspective, Speculative)
- [x] contextual-rag скилл (5 паттернов RAG, LanceDB, GraphRAG)
- [x] cost-optimization скилл (маршрутизация Haiku/Sonnet/Opus, Prompt Caching, Batch API)
- [x] 5 агентов из rohitg00/awesome-claude-code-toolkit: mlops-engineer, vector-database-engineer, documentation-engineer, kubernetes-specialist, terraform-engineer
=======
- [x] Obsidian vault синхронизация (Junction Point + MCP mcpvault)
>>>>>>> Stashed changes

---

## Идеи

### 1c-data-analyst — AI-аналитик данных 1С на базе Claude Code
- **Концепция:** Агент, который отвечает на вопросы по данным базы 1С на естественном языке
- **Как работает:**
  1. Пользователь задаёт вопрос ("Сколько продаж за март?", "Топ-5 контрагентов по обороту")
  2. Агент через MCP RAQ 1C находит нужные объекты/реквизиты метаданных
  3. Генерирует запрос 1С (по правилам `1c-rules.md`)
  4. Выполняет через `1c-queries` скилл (HTTP-сервис)
  5. Форматирует и возвращает ответ
- **Уже есть:** MCP RAQ 1C (метаданные), 1c-queries (выполнение), bsl-context (синтаксис), 1c-rules.md (правила запросов)
- **Нужно создать:** агент `1c-data-analyst` (промпт + оркестрация)
- **Требования для запуска:** Docker Desktop + HTTP-сервис запросов в базе 1С
- **Статус:** Идея

---

<<<<<<< Updated upstream
*Последнее обновление: 2026-03-16*
=======
### Obsidian Vault: 1С Analyst Workspace
- **Что:** Экосистема знаний аналитика 1С в Obsidian (14 зон, 27 заметок, ~170 связей)
- **Roadmap:** `1С Экосистема/12 — Развитие/Развитие — Индекс.md`
- **Текущая фаза:** Фаза 2 — Ядро знаний (~60%)
- **Следующий шаг:** дозаполнить Фазу 2 (процессы, БСП, запросы), установить Dataview
- **Статус:** В работе

---

*Последнее обновление: 2026-03-15*
>>>>>>> Stashed changes
