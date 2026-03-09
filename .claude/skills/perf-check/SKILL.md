---
name: perf-check
description: "Проверка производительности: N+1, blocking I/O, bundle size, ре-рендеры"
---

# /perf-check — Проверка производительности

## Когда использовать
После добавления новых API, компонентов с данными, обработки файлов.

## Инструкции

### 1. Backend (FastAPI)
1. **N+1 запросы**: Ищи циклы с запросами внутри (for + await/query)
2. **Blocking I/O**: В async функциях не должно быть:
   - `open()` без `aiofiles`
   - `time.sleep()` — используй `asyncio.sleep()`
   - `requests.get()` — используй `httpx.AsyncClient`
   - `subprocess.run()` без `asyncio.create_subprocess`
3. **Большие файлы**: Чтение целиком в память vs streaming
4. **Сериализация**: Большие Pydantic модели — используется `.model_dump()` с `exclude`?
5. **Кэширование**: Повторные тяжёлые операции кэшируются?

### 2. Frontend (Next.js/React)
1. **Bundle size**: Проверь `package.json` на тяжёлые зависимости:
   - `moment.js` → замени на `date-fns` или `dayjs`
   - `lodash` (полный) → `lodash-es` или отдельные импорты
2. **Ре-рендеры**:
   - Компоненты с `useEffect` без deps array?
   - Передача `{}` или `[]` как props (новый объект каждый рендер)?
   - Отсутствует `useMemo`/`useCallback` для тяжёлых вычислений?
3. **Images**: Используется `next/image` с оптимизацией?
4. **Data fetching**:
   - TanStack Query с правильным `staleTime`?
   - Нет fetch в useEffect (должен быть через TanStack Query)?

### 3. Общее
- Нет `console.log` в production коде
- Нет `debugger` statements
- Таймауты настроены для внешних вызовов

## Формат отчёта

```
## ⚡ Проверка производительности

### Backend
- N+1 паттерны: {N найдено}
- Blocking I/O в async: {N найдено}
- Проблемы с памятью: {описание}

### Frontend
- Тяжёлые зависимости: {список}
- Лишние ре-рендеры: {N мест}
- console.log в проде: {N}

### Критические проблемы
{описание}

### Вердикт: PASS / FAIL
```
