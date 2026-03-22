# Agent Runtime

Рабочее пространство для мульти-агентных команд (Agent Teams).
Делает взаимодействие агентов явным и проверяемым.

## Структура

- `shared/` — промежуточные артефакты между агентами (raw-data.json, articles.json)
- `messages/` — handoff-сообщения между агентами
- `state/` — план, статус-доска, служебные заметки
- `outputs/` — финальные результаты (report.pdf, briefing.md)

## Протокол

1. Каждый агент перед началом читает текущий plan.md
2. Каждый важный результат записывается в файл (не только в чат)
3. Каждый handoff создаёт сообщение в `messages/`
4. Каждый блокер создаёт сообщение с тегом `blocker`
5. Pipeline не завершён, пока coordinator не написал финальный briefing

## Очистка между запусками

```bash
rm -rf agent-runtime/shared/* agent-runtime/messages/* agent-runtime/state/*
# outputs/ сохраняются
```
