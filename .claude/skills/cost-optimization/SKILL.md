---
name: cost-optimization
description: >
  Оптимизация стоимости Claude API: маршрутизация моделей Haiku/Sonnet/Opus,
  Prompt Caching (экономия до 90%), батчинг запросов, Extended Thinking контроль.
  Применять при проектировании multi-agent систем или при высоких расходах на токены.
user-invocable: true
---

# Cost Optimization — Оптимизация стоимости Claude

## Правило 1: Маршрутизация моделей

### Выбор модели по задаче

| Задача | Модель | Экономия vs Opus |
|--------|--------|-----------------|
| Read-only анализ, поиск по файлам | **Haiku 4.5** | ~20x дешевле |
| Генерация кода, рефакторинг | **Sonnet 4.6** | ~5x дешевле |
| Архитектурные решения, сложный дебаг | **Opus 4.6** | baseline |
| Оркестрация multi-agent | **Sonnet 4.6** | ~5x дешевле |
| Простые агенты-воркеры (частые вызовы) | **Haiku 4.5** | ~20x дешевле |

### Правило "90% Haiku"

Haiku 4.5 = ~90% возможностей Sonnet при 1/3 стоимости.

Использовать Haiku для:
- Агентов code-scout, research-fetcher (read-only)
- Валидации и проверок (lint, type-check)
- Генерации шаблонного кода
- Параллельных воркеров в MapReduce

Использовать Sonnet для:
- Основных задач разработки
- Оркестрации субагентов
- Объяснений и документации

Использовать Opus только для:
- Архитектурных решений (1c-code-architect)
- Сложной многошаговой отладки
- Финального code review на критичных изменениях

### В агентах

```yaml
# Воркер-агент
---
name: my-worker-agent
model: haiku
---

# Оркестратор
---
name: my-orchestrator
model: sonnet
---

# Сложный планировщик
---
name: my-planner
model: opus
---
```

---

## Правило 2: Prompt Caching (до 90% экономии)

### Как работает

Anthropic кеширует повторяющийся префикс промпта на 5 минут (Standard) или 1 час (Extended).

**Стоимость кеша:**
- Запись: 25% от обычной цены (разово)
- Чтение: **10% от обычной цены** (каждый раз)

### Что кешировать

```python
# ХОРОШО: большой стабильный контекст в начале
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": LARGE_SYSTEM_CONTEXT,  # 10k+ токенов
                "cache_control": {"type": "ephemeral"}  # кешируй это
            },
            {
                "type": "text",
                "text": user_query  # меняется каждый раз
            }
        ]
    }
]

# ПЛОХО: кешировать маленький контекст (overhead > выгода)
# Кеш полезен от ~1024 токенов
```

### Применение к 1С агентам

```python
# При анализе кода — кешировать все правила и спецификации
cached_context = """
{FULL_1C_RULES_MD}      # 8000 токенов — кешируется
{FULL_SPEC_DOCS}        # 15000 токенов — кешируется
"""

# Только вопрос меняется
user_query = "Проверь этот код на антипаттерны"
```

**Экономия для 1С-агентов:**
- 1c-code-reviewer: 1c-rules.md (8k токенов) = кешировать → -85% на reviews
- 1c-feature-dev: все 9 фаз + спецификации = кешировать контекст → -70% за сессию

### Проверить что кеш работает

В ответе API поля `cache_read_input_tokens > 0` подтверждают работу кеша.

---

## Правило 3: Extended Thinking — контроль бюджета

### Когда отключать

Extended Thinking потребляет до 31,999 токенов за вызов:

```bash
# Отключить для всех задач (экономия):
export MAX_THINKING_TOKENS=0

# Ограничить для большинства задач:
export MAX_THINKING_TOKENS=5000

# Включить полностью только для сложных:
export MAX_THINKING_TOKENS=31999
```

### Рекомендуемые уровни

| Ситуация | Бюджет токенов |
|----------|---------------|
| CRUD, простой код | 0 (отключить) |
| Обычная разработка | 5,000 |
| Архитектура, debug | 15,000 |
| Сложное исследование | 31,999 |

---

## Правило 4: Батчинг (50% скидка)

Batch API: отправить N запросов асинхронно → ответ в течение 24 часов → **50% дешевле**.

```python
import anthropic

client = anthropic.Anthropic()

# Создать батч
batch = client.messages.batches.create(
    requests=[
        {"custom_id": f"req-{i}", "params": {"model": "claude-haiku-4-5", ...}}
        for i in range(100)
    ]
)

# Получить результаты (poll)
while batch.processing_status == "in_progress":
    time.sleep(60)
    batch = client.messages.batches.retrieve(batch.id)
```

**Когда использовать батчинг:**
- Массовая обработка документов (не real-time)
- Генерация эмбеддингов для RAG индексирования
- Ночная пакетная аналитика
- Оффлайн code review для больших PR

---

## Правило 5: Контекст — меньше = дешевле

### Обрезка контекста

```python
# Сохранять только релевантные части диалога
def trim_context(messages, max_tokens=8000):
    # Всегда сохраняй: system + последние N сообщений
    system = [m for m in messages if m["role"] == "system"]
    recent = messages[-10:]  # последние 10 обменов
    return system + recent
```

### Компрессия (ConversationSummary)

```python
# При длинных сессиях — сжимай историю
if token_count(messages) > 50000:
    summary = claude("Summarize this conversation in 500 words", messages)
    messages = [system_message, {"role": "assistant", "content": summary}]
```

### Для Claude Code

- Используй `/compact` при большом контексте
- `PreCompact` хук уже настроен для сохранения STATE.md
- Агенты с `maxTurns` ограничены автоматически

---

## Калькулятор стоимости (примерно)

| Сценарий | Без оптимизации | С оптимизацией | Экономия |
|----------|----------------|----------------|----------|
| Code review (50 rev/день) | $15/день | $1.5/день | 90% |
| 1С feature dev (3 ч) | $8 | $2 | 75% |
| RAG индексирование (1000 docs) | $20 | $2 | 90% |
| Multi-agent analysis (10 агентов) | $5 | $1 | 80% |

---

## Чеклист перед деплоем multi-agent системы

- [ ] Воркеры используют Haiku, оркестраторы — Sonnet
- [ ] Большой стабильный контекст помечен `cache_control`
- [ ] `MAX_THINKING_TOKENS` установлен адекватно задаче
- [ ] Неинтерактивные задачи → Batch API
- [ ] `maxTurns` установлен для всех агентов
- [ ] Контекст обрезается при превышении 50k токенов
