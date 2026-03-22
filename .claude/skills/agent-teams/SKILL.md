---
name: agent-teams
description: Запуск мульти-агентной команды (Agent Teams) — динамический pipeline из 7 ролей. Исследования, разработка, ревью, тестирование — силами нескольких агентов параллельно.
---

# Agent Teams — Мульти-агентный Pipeline

## Что это

Экспериментальная фича Claude Code: lead-агент запускает тиммейтов, которые работают как отдельные Claude Code сессии. Pipeline формируется динамически на основе задачи.

## Требования

- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — включено в settings.local.json
- Permissions: Read, Write, Edit, Glob, Grep, WebSearch, WebFetch — в allowlist
- **tmux** (опционально) — для визуального режима через WSL Ubuntu

## Доступные роли (7)

### Исследование и аналитика
| Роль | Агент | Назначение |
|------|-------|-----------|
| **scraper** | `team-scraper.md` | Сбор данных: WebSearch + WebFetch из интернета |
| **analyst** | `team-analyst.md` | Анализ: relevance scoring, тренды, тональность |
| **reporter** | `team-reporter.md` | Отчёты: markdown, PDF |

### Разработка
| Роль | Агент | Назначение |
|------|-------|-----------|
| **architect** | `team-architect.md` | Анализ кодовой базы, проектирование, план реализации |
| **coder** | `team-coder.md` | Написание кода по плану architect |
| **reviewer** | `team-reviewer.md` | Ревью: качество, безопасность, соответствие плану |
| **tester** | `team-tester.md` | Тесты: unit, integration, покрытие 80%+ |

## Pipelines (динамические)

Pipeline выбирается автоматически на основе задачи:

### Research — исследование и отчёт
```
scraper → analyst → reporter → briefing
```
Для: мониторинг новостей, обзор технологий, конкурентный анализ

### Quick Fix — баг или мелкая правка
```
coder → reviewer → briefing
```
Для: "исправь баг", "поменяй X на Y"

### Feature — новая фича
```
architect → coder → reviewer → tester → briefing
```
Для: "добавь фичу", "реализуй"

### Full Cycle — фича с исследованием
```
scraper → analyst → architect → coder → reviewer → tester → briefing
```
Для: "изучи как делают X и реализуй у нас"

### Plan Only — только проектирование
```
architect → briefing
```
Для: "спланируй", "спроектируй", "как лучше сделать"

### Complete — полный цикл с отчётом
```
scraper → analyst → architect → coder → reviewer → tester → reporter → briefing
```
Для: полный R&D цикл

## Протокол работы

Каждый агент:
1. Получает задание через **SendMessage** от предыдущего
2. Читает входные данные из `agent-runtime/shared/`
3. Создаёт свой артефакт в `agent-runtime/shared/`
4. Отправляет **SendMessage** следующему с кратким саммари

### Revision Loop (dev pipeline)
Если reviewer вернул REQUEST_CHANGES:
```
reviewer → coder (исправления) → reviewer (повторная проверка)
```
Максимум 2 итерации, потом эскалация.

## Структура runtime

```
agent-runtime/
├── shared/               # Рабочие данные между агентами
│   ├── raw-data.json     # Данные от scraper
│   ├── articles.json     # Анализ от analyst
│   ├── architecture.md   # План от architect
│   ├── changes.md        # Список изменений от coder
│   ├── review.md         # Результат ревью
│   └── test-report.md    # Результат тестов
├── state/                # plan.md, status.md
├── messages/             # Handoff-сообщения
└── outputs/              # Финал: briefing.md, report.md
```

## Как запустить

### Через команду
```
/agent-team [описание задачи]
```

### Текстом
```
Создай Agent Team: [описание задачи].
Проект: projects/aether (Tauri + React + TypeScript).
```

## Примеры

### Исследование
```
/agent-team мониторинг новостей: AI coding tools 2026, EN и RU
```

### Фича
```
/agent-team добавь экспорт в PDF в проект projects/aether
```

### Фича с исследованием
```
/agent-team изучи лучшие практики drag-and-drop и реализуй в projects/aether
```

### Quick fix
```
/agent-team исправь баг: кнопка "Сохранить" не работает в SettingsPage.tsx
```

### Планирование
```
/agent-team спроектируй архитектуру мультиязычности для projects/stenograph
```

## Очистка между запусками

```bash
rm -rf agent-runtime/shared/* agent-runtime/messages/* agent-runtime/state/*
# outputs/ сохраняются
```

## Добавление новых ролей

Создай `.claude/agents/team-[роль].md` с секциями:
1. **Миссия** — что делает агент
2. **Как работать** — пошаговый алгоритм
3. **Контракт выхода** — какие файлы создаёт, кому SendMessage
4. **Формат данных** — схема входов/выходов
5. **Правила** — ограничения и fallback
