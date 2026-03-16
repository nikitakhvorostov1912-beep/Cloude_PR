---
description: Контракт API между FastAPI и Next.js. OpenAPI → TypeScript типы, fetch-обёртки, валидация. Используй при создании/изменении API endpoints.
---

# API Contract: FastAPI ↔ Next.js

## Принцип

Единый источник правды — **FastAPI Pydantic модели**. TypeScript типы генерируются из OpenAPI.

## Генерация типов

```bash
# Из работающего FastAPI сервера
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts

# Из сохранённого файла
npx openapi-typescript openapi.json -o src/types/api.ts
```

## Формат ответа API

```python
# Backend: единый envelope
class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: str | None = None
```

```typescript
// Frontend: типизированный envelope
interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: string | null
}
```

## Fetch-обёртка

```typescript
// lib/api.ts
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  })
  const json: ApiResponse<T> = await res.json()
  if (!json.success) throw new Error(json.error ?? "Unknown error")
  return json.data as T
}

// Использование
const items = await api<Item[]>("/api/items")
const item = await api<Item>("/api/items", {
  method: "POST",
  body: JSON.stringify({ name: "Test", price: 9.99 }),
})
```

## Проверка контракта

```bash
# 1. FastAPI запущен → экспорт OpenAPI
curl http://localhost:8000/openapi.json > openapi.json

# 2. Генерация TS типов
npx openapi-typescript openapi.json -o src/types/api.ts

# 3. Проверка компиляции
npx tsc --noEmit
```

## Маршруты

| Backend (FastAPI) | Frontend (fetch) |
|-------------------|-----------------|
| `GET /api/items` | `api<Item[]>("/api/items")` |
| `POST /api/items` | `api<Item>("/api/items", { method: "POST", body })` |
| `GET /api/items/{id}` | `api<Item>(\`/api/items/${id}\`)` |
| `PUT /api/items/{id}` | `api<Item>(\`/api/items/${id}\`, { method: "PUT", body })` |
| `DELETE /api/items/{id}` | `api<void>(\`/api/items/${id}\`, { method: "DELETE" })` |

## Чеклист при добавлении endpoint

- [ ] Pydantic модель для request body
- [ ] Pydantic модель для response (response_model)
- [ ] ApiResponse envelope
- [ ] Перегенерировать TS типы
- [ ] Обновить fetch-обёртку если нужно
- [ ] Проверить `tsc --noEmit`
