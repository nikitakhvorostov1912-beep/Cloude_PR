---
name: api-contract
description: "Проверка API контрактов: Pydantic ↔ TypeScript, schema drift, валидация"
---

# /api-contract — Проверка API контрактов

## Когда использовать
После изменений в API endpoints или TypeScript типах. Предотвращает рассинхрон backend ↔ frontend.

## Инструкции

### 1. Собери API endpoints
1. Найди все `@app.get`, `@app.post`, `@app.put`, `@app.delete`, `@router.*` в backend
2. Для каждого endpoint запиши:
   - HTTP метод + путь
   - Request body (Pydantic модель)
   - Response model
   - Query/Path параметры

### 2. Собери Frontend API вызовы
1. Найди все `fetch()`, `axios`, TanStack Query хуки в frontend
2. Для каждого вызова запиши:
   - URL + метод
   - Тело запроса (TypeScript тип)
   - Ожидаемый ответ (TypeScript тип)

### 3. Сравни контракты
Для каждого endpoint проверь:
- URL в frontend совпадает с backend?
- Поля request body совпадают? (имена, типы, обязательность)
- Поля response совпадают?
- HTTP метод совпадает?
- Error responses обрабатываются на frontend?

### 4. Валидация Pydantic моделей
- Все поля имеют валидаторы (min/max, regex)?
- Optional поля правильно обработаны?
- Enum значения синхронизированы?

## Формат отчёта

```
## 🔗 Проверка API контрактов

### Endpoints: {N} всего

| Endpoint | Backend Model | Frontend Type | Статус |
|----------|--------------|---------------|--------|

### Рассинхроны
{файл:строка — описание расхождения}

### Непокрытые endpoints
{endpoints без фронтенд вызовов}

### Вердикт: PASS / FAIL
```
