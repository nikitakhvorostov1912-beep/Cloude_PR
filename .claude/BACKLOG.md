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

*Последнее обновление: 2026-03-06*
