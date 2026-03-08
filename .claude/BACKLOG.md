# 📋 Бэклог — Задачи на будущее

> Список инструментов, идей и задач для установки/интеграции.
> Обновляется по мере обнаружения интересных проектов.

---

## 🔧 К установке / интеграции

### 1. AIChat — Универсальный CLI для LLM
- **Репо:** https://github.com/sigoden/aichat
- **Что:** Единый CLI для 20+ LLM-провайдеров (OpenAI, Claude, Gemini, Ollama, Deepseek и др.)
- **Зачем:** Shell Assistant (NL→команды), локальный OpenAI-совместимый прокси (`aichat --serve`), RAG из коробки, MCP поддержка, LLM Arena
- **Установка:** `cargo install aichat` / `scoop install aichat` (Windows)
- **Приоритет:** 🟡 Средний
- **Статус:** ⏳ Ожидает

### ~~2. Xonsh — Python-powered Shell~~ ✅ Установлен
- **Репо:** https://github.com/xonsh/xonsh
- **Версия:** v0.22.6
- **Статус:** ✅ Установлен

### ~~3. E2B Fragments — AI-генератор приложений~~ ✅ Установлен
- **Репо:** https://github.com/e2b-dev/fragments
- **Путь:** `tools/fragments/`
- **Статус:** ✅ Установлен (нужен E2B_API_KEY для запуска)

### 4. Unity MCP — AI-мост к Unity Editor
- **Репо:** https://github.com/CoplayDev/unity-mcp
- **Что:** MCP-сервер для управления Unity Editor через Claude/Cursor. 30+ инструментов, ⭐ 6.7k
- **Зачем:** AI-управление сценами, ассетами, скриптами Unity через натуральный язык
- **Приоритет:** 🔵 Низкий (пока не нужен)
- **Статус:** ⏳ На заметке

### 8. Claude Scientific Skills — 170+ научных скиллов
- **Репо:** https://github.com/K-Dense-AI/claude-scientific-skills
- **Что:** 170 скиллов для научных исследований, 250+ баз данных, 60+ Python-пакетов
- **Домены:** биоинформатика, хеминформатика, drug discovery, медицинская визуализация, физика, астрономия
- **Приоритет:** 🔵 Низкий (нишевый научный проект)
- **Статус:** ⏳ На заметке

### 9. AI Research Skills — 85 скиллов для AI/ML research
- **Репо:** https://github.com/Orchestra-Research/AI-Research-SKILLs
- **Что:** 85 скиллов в 21 категории: архитектуры моделей, fine-tuning, distributed training, inference, RAG, MLOps, safety
- **Установка:** `npx @orchestra-research/ai-research-skills`
- **Приоритет:** 🔵 Низкий (нужен когда начнётся ML/AI проект)
- **Статус:** ⏳ На заметке

### 10. Casibase — Open-source AI Cloud OS
- **Репо:** https://github.com/casibase/casibase
- **Что:** AI-платформа с RAG knowledge base, SSO, 20+ LLM, MCP/A2A координация, speech/vision
- **Стек:** Go + React + MySQL + Docker/K8s, ⭐ 4.5k
- **Приоритет:** 🔵 Низкий (enterprise-платформа, overkill для текущих задач)
- **Статус:** ⏳ На заметке

### 11. Serena — Semantic Code Navigation MCP
- **Репо:** https://github.com/oraios/serena
- **Что:** MCP-сервер для символьной навигации по коду через LSP (30+ языков)
- **Фишка:** `find_symbol`, `insert_after_symbol` вместо файловых операций — экономит токены на крупных кодовых базах
- **Стек:** Python, LSP, MCP SDK, JetBrains plugin
- **Приоритет:** 🔵 Низкий (вернуться если будут проблемы с навигацией по большим проектам)
- **Статус:** ⏳ На заметке

### 12. BSL Atlas — Семантический поиск по коду 1С
- **Репо:** https://github.com/Arman-Kudaibergenov/bsl-atlas
- **Что:** MCP-сервер: векторный поиск, структурный индекс и граф вызовов по коду конфигурации 1С
- **Фишка:** Два режима — быстрый (SQLite) и полный (ChromaDB + embeddings). Поиск по описанию: "как реализовано проведение"
- **Зачем:** Дополняет bsl-context (API платформы) анализом кода конфигурации. Подключать когда появится реальная конфигурация для анализа
- **Стек:** Python, SQLite, ChromaDB, Qwen3 embeddings, 37 звёзд, MIT
- **Приоритет:** 🟡 Средний (нужна реальная конфигурация)
- **Статус:** ⏳ Ожидает

### 13. METR — MCP Test Runner для 1С
- **Репо:** https://github.com/alkoleft/mcp-onec-test-runner
- **Что:** MCP-сервер для запуска YaXUnit тестов, сборки проектов и проверки синтаксиса через AI
- **Зачем:** Автотесты из Claude Code → написал код → запустил тесты → получил результат. Усилит Phase 7 в 1c-feature-dev
- **Стек:** Kotlin, JDK 17+, 1С 8.3.10+, YaXUnit, 76 звёзд, GPL-3.0
- **Приоритет:** 🟡 Средний (нужен YaXUnit в проекте)
- **Статус:** ⏳ Ожидает

### 16. 1c_mcp — MCP-сервер для доступа к живой базе 1С
- **Репо:** https://github.com/vladimir-kharin/1c_mcp
- **Что:** MCP-сервер на платформе 1С — даёт AI прямой доступ к данным, метаданным и бизнес-логике живой базы
- **Фишка:** CFE-расширение + Python-прокси (OAuth2, stdio transport). AI автономно запрашивает нужные данные через tools/resources/prompts
- **Зачем:** Дополняет bsl-context (синтаксис) и MCP RAQ (поиск метаданных) — этот даёт доступ к реальным данным базы
- **Стек:** 1C Enterprise + Python, ⭐ 296, MIT
- **Приоритет:** 🟡 Средний (нужна опубликованная база с HTTP-сервисом)
- **Статус:** ⏳ Ожидает

### 15. OpenIntegrations — Библиотека интеграций 1С с 30+ сервисами
- **Репо:** https://github.com/Bayselonarrend/OpenIntegrations
- **Что:** Готовые методы интеграции 1С с Telegram, Bitrix24, Google, Yandex, PostgreSQL, S3, Slack, Notion, Airtable и др.
- **Формат:** CFE-расширение, OneScript-пакет, CLI (Windows/Linux)
- **Стек:** 1C Enterprise, ⭐ 560, MIT, v1.33.0 (март 2026)
- **Зачем:** Справочник готовых методов при задачах на интеграцию 1С с внешними API
- **Приоритет:** 🔵 Низкий (подключать когда появится задача на интеграцию)
- **Статус:** ⏳ На заметке

### ~~14. MCP RAQ 1C — RAG-поиск по метаданным конфигурации~~ ✅ Установлен
- **Репо:** https://github.com/Antiloop-git/MCP-RAQ-1C
- **Путь:** `tools/mcp-raq-1c/`
- **Запуск:** `tools/mcp-raq-1c/start.bat` (5 Docker-контейнеров), MCP endpoint: `http://localhost:8000/sse`
- **Бонус:** скилл `1c-queries` скопирован в `.claude/skills/` (запросы к базе 1С через HTTP-сервис)
- **Статус:** ✅ Установлен (требует Docker Desktop + XML-выгрузку конфигурации для индексации)

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

---

## ✅ Выполненные

- [x] Deep Researcher агент (deep-researcher + research-fetcher)
- [x] Code Scout, Code Reviewer, Bug Hunter агенты
- [x] Хуки (Stop, SubagentStop)
- [x] Composio MCP интеграция
- [x] UI/UX Pro Max обновление
- [x] Pake CLI установка
- [x] Everything Claude Code (ECC) интеграция — 16 агентов, 80+ скиллов
- [x] Xonsh v0.22.6 (Python-powered shell)
- [x] E2B Fragments (AI-генератор приложений, tools/fragments/)
- [x] Marketing Skills (32 скилла, .claude/skills/marketing/)
- [x] Claude Monitor v3.1.0 (claude-monitor / ccm)
- [x] Awesome Subagents — 6 лучших из 103 (performance-engineer, api-designer, docker-expert, mcp-developer, devops-engineer, prompt-engineer)
- [x] Memory Management скилл (3-уровневая иерархия)

---

## 💡 Идеи

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
- **Вдохновение:** github.com/msrv-tech/AI_agent (27 звёзд) — аналог, но отдельное приложение на Qwen
- **Преимущество:** Не отдельное приложение, а нативная часть Claude Code. Claude вместо Qwen. Все правила 1С уже загружены
- **Статус:** 💡 Идея

---

*Последнее обновление: 2026-03-09*
