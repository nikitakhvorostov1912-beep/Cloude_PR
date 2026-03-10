#!/usr/bin/env bash

# Session Boot — автоматическая загрузка контекста при старте сессии
# Уровень 1: контекст + статус + доступные инструменты

# Git info
BRANCH=$(git -C "D:/Cloude_PR" branch --show-current 2>/dev/null || echo "unknown")
LAST_COMMITS=$(git -C "D:/Cloude_PR" log --oneline -5 2>/dev/null || echo "no commits")
GIT_STATUS=$(git -C "D:/Cloude_PR" status --short 2>/dev/null | head -10)
STASH_COUNT=$(git -C "D:/Cloude_PR" stash list 2>/dev/null | wc -l)

cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "## Session Boot — Контекст загружен\n\n### Проект: Cloude_PR\n- Стек: Python 3.12 (FastAPI, Pydantic v2) + Next.js 15 (React 19, shadcn/ui, Tailwind CSS 4)\n- Ветка: ${BRANCH}\n- Последние коммиты:\n${LAST_COMMITS}\n- Изменённые файлы: ${GIT_STATUS:-нет изменений}\n- Stash: ${STASH_COUNT} записей\n\n### Доступные инструменты\n**Агенты (53):** code-scout (быстрая разведка), code-explorer (глубокий анализ), code-architect (проектирование), code-reviewer (ревью), bug-hunter (отладка), deep-researcher (исследования), 1c-code-* (5 агентов 1С), bpm-* (4 BPMN агента)\n\n**Ключевые скиллы:** /brainstorm, /quality-gate, /health-check, /debug, /research, /code-review, /feature-dev, /fastapi-patterns, /nextjs-patterns, /api-contract\n\n**1С скиллы (67):** /epf-*, /erf-*, /form-*, /skd-*, /db-*, /cf-*, /cfe-*, /meta-*\n\n**MCP:** context7 (документация библиотек), playwright (browser automation)\n\n### Smart Router — автоматический подбор\nЯ буду автоматически подключать нужные скиллы и агенты по теме твоего запроса:\n- Код/фичи → fastapi-patterns, nextjs-patterns, code-scout\n- 1С → 1c-rules, 1c-feature-dev, bsl-context MCP\n- Баг → bug-hunter, debug\n- Обследование → 1c-survey-methodology, process-extraction\n- Ревью → code-reviewer, quality-gate\n\n### Правила\n- Все тексты на русском\n- Тёмная тема\n- Перед коммитом: тесты + билд + preview\n- Хуки: авто-линт (PostToolUse Edit), проверка дублей (PostToolUse Write), Stop guard, SubagentStop guard"
  }
}
EOF

exit 0
