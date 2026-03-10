# /boot — Полная диагностика проекта

Выполни комплексную проверку workspace и всех подпроектов. Результат — краткий отчёт со статусами.

## Чек-лист

### 1. Git статус
- Текущая ветка и отставание от master
- Незакоммиченные изменения
- Stash записи

### 2. Backend (survey-automation)
- Проверь наличие `projects/survey-automation/backend/`
- Проверь `python --version` и наличие venv
- Попробуй запустить: `cd projects/survey-automation/backend && python -c "from app.config import get_config; print('OK:', get_config().app.title)"` (если есть)
- Проверь структуру файлов (main.py, app/, data/)

### 3. Frontend (survey-automation)
- Проверь наличие `projects/survey-automation/frontend/`
- Проверь `node --version`
- Проверь `package.json` существует
- Попробуй: `npm run build` (если есть)

### 4. Подпроекты
- `voice-agent-1c/` — проверь наличие и основные файлы
- `ai-ecosystem-1c/` — проверь наличие и основные файлы

### 5. Инфраструктура Claude Code
- Посчитай агентов: `~/.claude/agents/*.md` + `.claude/agents/*.md` (если есть)
- Посчитай скиллов: `~/.claude/skills/*/SKILL.md` + `.claude/skills/*/SKILL.md`
- Посчитай команд: `~/.claude/commands/*.md` + `.claude/commands/**/*.md`
- Проверь хуки в `.claude/settings.local.json`
- Проверь MCP серверы в `.mcp.json`

### 6. Launch серверы
- Прочитай `.claude/launch.json` и покажи доступные серверы

## Формат отчёта

```
## Boot Report

| Компонент | Статус | Детали |
|-----------|--------|--------|
| Git       | OK/WARN | ветка, изменения |
| Backend   | OK/FAIL | версия python, venv |
| Frontend  | OK/FAIL | версия node, билд |
| voice-agent-1c | OK/MISSING | |
| ai-ecosystem-1c | OK/MISSING | |
| Агенты    | OK | N глобальных + M проектных |
| Скиллы    | OK | N глобальных + M проектных |
| Команды   | OK | N глобальных + M проектных |
| Хуки      | OK | список активных |
| MCP       | OK/WARN | список серверов |
| Серверы   | OK | список из launch.json |

Время проверки: X сек
```

Не запускай dev-серверы. Только проверяй наличие и конфигурацию.
