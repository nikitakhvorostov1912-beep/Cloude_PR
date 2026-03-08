---
name: n8n-workflow-patterns
description: Build production-ready n8n workflows using proven architectural patterns. Use when creating n8n automations, connecting nodes, designing webhook/API/scheduled workflows, or troubleshooting n8n expression syntax.
---

# n8n Workflow Patterns

Создание production-ready n8n воркфлоу по проверенным архитектурным паттернам.

> Источник: https://github.com/czlonkowski/n8n-skills (7 скиллов)

## Когда использовать

- Создание n8n воркфлоу
- Подключение нод и настройка выражений
- Дизайн автоматизаций (webhook, API, scheduled)
- Отладка n8n выражений и ошибок валидации

## 5 архитектурных паттернов

### 1. Webhook Processing

```
Webhook Trigger → Validate Input → Process Data → Respond
                                  ↓
                            Error Handler → Notify
```

- Всегда валидировать входящие данные
- Отвечать сразу (200), обрабатывать асинхронно
- Логировать все входящие запросы

### 2. HTTP API Integration

```
Trigger → Auth Setup → API Call → Parse Response → Transform → Output
                                 ↓
                           Retry Logic → Error Handler
```

- Использовать HTTP Request ноду с retry
- Хранить API ключи в credentials, НЕ в нодах
- Пагинация через Loop Over Items

### 3. Database Operations

```
Trigger → Query DB → Transform → Conditional → Update DB → Confirm
```

- Параметризованные запросы (без SQL injection)
- Batch-операции для больших объёмов
- Transaction-подобные паттерны через IF + Error Handler

### 4. Scheduled Tasks (Cron)

```
Schedule Trigger → Check Conditions → Execute → Log Result → Notify
```

- Идемпотентные операции (безопасный повторный запуск)
- Логировать каждый запуск
- Уведомления об ошибках

### 5. AI Agent Workflow

```
Trigger → Prepare Context → AI Agent → Parse Output → Action → Respond
                           ↕
                     Tool Calls (HTTP, DB, Code)
```

- Структурированные промпты
- Парсинг и валидация AI-ответов
- Fallback на ручную обработку

## Синтаксис выражений n8n

### Доступ к данным
```javascript
// Текущая нода
{{ $json.fieldName }}
{{ $json["field with spaces"] }}

// Предыдущая нода
{{ $('Node Name').item.json.field }}

// Все элементы
{{ $('Node Name').all() }}

// Первый/последний
{{ $('Node Name').first().json.field }}
{{ $('Node Name').last().json.field }}
```

### Частые ошибки
```javascript
// НЕПРАВИЛЬНО
{{ $json.data.items }}        // если data может быть undefined
{{ $node.name.json.field }}   // устаревший синтаксис

// ПРАВИЛЬНО
{{ $json.data?.items ?? [] }}
{{ $('Node Name').item.json.field }}
```

### Полезные функции
```javascript
// Дата/время
{{ $now.toISO() }}
{{ $now.minus({ days: 7 }).toISO() }}

// Условия
{{ $json.status === 'active' ? 'да' : 'нет' }}

// Массивы
{{ $json.items.map(i => i.name).join(', ') }}
```

## Валидация и отладка

### Частые ошибки валидации
| Ошибка | Причина | Решение |
|--------|---------|---------|
| Expression error | Неправильный синтаксис `{{ }}` | Проверить кавычки, скобки |
| Node not found | Имя ноды не совпадает | Точное имя в `$('...')` |
| Cannot read property | Данные отсутствуют | Optional chaining `?.` |
| Timeout | Долгая операция | Увеличить timeout, разбить на части |

### False Positives
- n8n иногда показывает warnings для корректных выражений
- Проверять выполнением, а не только визуально

## Best Practices

1. **Именование нод** — описательные имена (не "HTTP Request", а "Fetch User Data")
2. **Error handling** — Error Trigger нода в каждом workflow
3. **Credentials** — через UI, никогда в коде
4. **Тестирование** — Manual Execution перед активацией
5. **Документация** — Sticky Notes для описания логики
6. **Версионирование** — экспорт JSON в git
