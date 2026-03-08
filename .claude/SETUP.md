# Настройка workspace на новом устройстве

> Инструкция для восстановления полного рабочего пространства после клонирования с GitHub.

## 1. Клонирование

```bash
git clone https://github.com/nikitakhvorostov1912-beep/Cloude_PR.git
cd Cloude_PR
git checkout feature/workspace-setup
```

## 2. Восстановление памяти Claude Code

Память хранится вне репо в пользовательской директории Claude Code.
Бэкап лежит в `.claude/memory-backup/`.

```bash
# Windows
mkdir -p ~/.claude/projects/D--Cloude-PR/memory/
cp .claude/memory-backup/*.md ~/.claude/projects/D--Cloude-PR/memory/

# Путь может отличаться — проверь через:
# claude config get projectsDir
```

## 3. Установка Smithery-скиллов (symlinks)

24 скилла установлены через Smithery CLI. Для переустановки:

```bash
npx @smithery/cli@latest skill add anthropics-agent-identifier --agent claude-code
npx @smithery/cli@latest skill add anthropics-canvas-design --agent claude-code
npx @smithery/cli@latest skill add anthropics-frontend-design --agent claude-code
# ... и остальные (полный список в .claude/skills/ — все symlinks)
```

Или восстанови вручную — исходники в `.agents/skills/` (если есть).

## 4. MCP-серверы

Добавь в `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "bsl-context": {
      "command": "java",
      "args": ["-jar", "path/to/mcp-bsl-context.jar", "--platform-path", "C:/Program Files/1cv8/8.3.XX.YYYY"]
    }
  }
}
```

Требуется: Java 17+, платформа 1С 8.3.20+

## 5. MCP RAQ 1C (Docker)

```bash
cd tools/
git clone https://github.com/Antiloop-git/MCP-RAQ-1C.git mcp-raq-1c
cd mcp-raq-1c
# Запуск: start.bat (5 Docker-контейнеров)
# Endpoint: http://localhost:8000/sse
```

Требуется: Docker Desktop

## 6. Python окружение

```bash
# Voice Agent
cd voice-agent-1c
python -m venv venv
venv/Scripts/activate  # Windows
pip install -r requirements.txt
cp .env.example .env   # заполнить ключи

# AI Ecosystem
cd ai-ecosystem-1c
python -m venv venv
pip install -r requirements.txt
cp .env.example .env
```

## 7. Node.js окружение

```bash
# Voice Agent Dashboard
cd voice-agent-1c/dashboard
npm install

# AI Ecosystem Dashboard
cd ai-ecosystem-1c/dashboard
npm install

# Survey Automation Frontend
cd projects/survey-automation/frontend
npm install
```

## 8. Секреты (.env файлы)

Создай `.env` по шаблонам `.env.example` в каждом проекте.
Ключи:
- `ANTHROPIC_API_KEY` — Claude API
- `YANDEX_CLOUD_API_KEY` — STT/TTS
- `MANGO_API_KEY` — Телефония
- `TELEGRAM_BOT_TOKEN` — Уведомления

## 9. Composio MCP

```bash
npx composio login
# Следуй инструкциям для OAuth
```

## 10. Проверка

```bash
claude  # Запусти Claude Code в директории проекта
# Проверь:
# - /health-check — работает ли workspace
# - Скиллы видны в автокомплите
# - Память загружается (спроси про события 1С)
```

---

*Последнее обновление: 2026-03-09*
