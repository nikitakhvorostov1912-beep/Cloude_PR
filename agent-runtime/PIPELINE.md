# Agent Teams — Pipelines

## Динамическое формирование

Pipeline выбирается автоматически на основе задачи. Coordinator анализирует запрос и собирает цепочку из 7 доступных ролей.

## Роли (7)

```
┌─────────────────────────────────────────────────┐
│  ИССЛЕДОВАНИЕ          scraper → analyst → reporter  │
│  Сбор данных, анализ, отчёты                        │
├─────────────────────────────────────────────────┤
│  РАЗРАБОТКА            architect → coder → reviewer → tester │
│  Проектирование, код, ревью, тесты                  │
├─────────────────────────────────────────────────┤
│  КООРДИНАЦИЯ           coordinator (team-lead)       │
│  Формирует pipeline, управляет, брифинг             │
└─────────────────────────────────────────────────┘
```

## Стандартные Pipelines

### Research — исследование
```
coordinator
     │
     ▼
 scraper ──→ shared/raw-data.json
     │        WebSearch + WebFetch
     ▼
 analyst ──→ shared/articles.json + analysis-summary.md
     │        Relevance, sentiment, тренды
     ▼
 reporter ──→ outputs/report.md
     │
     ▼
 coordinator ──→ outputs/briefing.md
```

### Feature — разработка фичи
```
coordinator
     │
     ▼
 architect ──→ shared/architecture.md
     │          Анализ кода, план реализации
     ▼
 coder ──→ shared/changes.md + код в проекте
     │      Реализация по плану
     ▼
 reviewer ──→ shared/review.md
     │         APPROVE / REQUEST_CHANGES / REJECT
     │
     ├─[REQUEST_CHANGES]──→ coder (revision loop, макс 2)
     │
     ▼
 tester ──→ shared/test-report.md + тесты в проекте
     │       Unit/integration тесты, покрытие
     ▼
 coordinator ──→ outputs/briefing.md
```

### Full Cycle — исследование + разработка
```
coordinator
     │
     ▼
 scraper ──→ analyst ──→ architect ──→ coder ──→ reviewer ──→ tester
     │                       │                       │
     │                       └── план на основе      └── revision loop
     │                           исследования
     ▼
 coordinator ──→ outputs/briefing.md
```

### Quick Fix — быстрая правка
```
coordinator → coder → reviewer → coordinator (briefing)
```

### Plan Only — проектирование
```
coordinator → architect → coordinator (briefing)
```

## Коммуникация

```
coordinator ──SendMessage──→ [первый агент]
                              "Задание: ..."

[агент N]   ──SendMessage──→ [агент N+1]
                              "Готово: артефакт в shared/..."

[последний] ──SendMessage──→ coordinator
                              "Pipeline завершён"
```

## Артефакты по ролям

| Роль | Создаёт | Читает |
|------|---------|--------|
| scraper | raw-data.json, scraper-log.md | — |
| analyst | articles.json, analysis-summary.md | raw-data.json |
| reporter | outputs/report.md, reporter-log.md | articles.json, analysis-summary.md |
| architect | architecture.md, architect-log.md | Код проекта (Read/Glob/Grep) |
| coder | changes.md, coder-log.md + код | architecture.md |
| reviewer | review.md, reviewer-log.md | changes.md, architecture.md, код |
| tester | test-report.md, tester-log.md + тесты | changes.md, review.md, код |

## Структура agent-runtime/

```
agent-runtime/
├── shared/                     # Рабочие данные
│   ├── raw-data.json           # scraper
│   ├── scraper-log.md          # scraper
│   ├── articles.json           # analyst
│   ├── analysis-summary.md     # analyst
│   ├── architecture.md         # architect
│   ├── architect-log.md        # architect
│   ├── changes.md              # coder
│   ├── coder-log.md            # coder
│   ├── review.md               # reviewer
│   ├── reviewer-log.md         # reviewer
│   ├── test-report.md          # tester
│   └── tester-log.md           # tester
├── state/                      # Координация
│   ├── plan.md                 # Pipeline план
│   └── status.md               # Текущий статус
├── messages/                   # Handoff-сообщения
│   └── message-template.md     # Шаблон
└── outputs/                    # Финальные результаты
    ├── briefing.md             # Coordinator
    ├── report.md               # Reporter
    └── report.pdf              # Reporter (если доступен)
```

## Revision Loop

При REQUEST_CHANGES от reviewer:
1. Coordinator читает review.md
2. Отправляет coder список конкретных правок
3. Coder исправляет → обновляет changes.md
4. Reviewer проверяет повторно
5. Максимум 2 итерации → эскалация coordinator

## Добавление новых ролей

Создай `.claude/agents/team-[роль].md`:
1. **Миссия** — что делает агент
2. **Как работать** — пошаговый алгоритм
3. **Контракт выхода** — файлы + SendMessage
4. **Формат данных** — JSON/MD schema
5. **Правила** — ограничения и fallback

Добавь роль в coordinator's таблицу ролей.
