---
description: Паттерны Next.js 15 + React 19 + shadcn/ui + Tailwind CSS 4. Используй при работе с фронтендом.
---

# Next.js 15 Patterns

## Структура проекта

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx        # Root layout (Server Component)
│   │   ├── page.tsx          # Home page
│   │   ├── globals.css       # Tailwind + CSS variables
│   │   └── {route}/
│   │       ├── page.tsx      # Route page
│   │       └── loading.tsx   # Suspense fallback
│   ├── components/
│   │   ├── ui/               # shadcn/ui компоненты
│   │   └── {feature}/        # Фича-компоненты
│   ├── lib/
│   │   ├── api.ts            # API клиент (fetch обёртки)
│   │   └── utils.ts          # cn() и утилиты
│   └── types/
│       └── index.ts          # Общие типы
├── tailwind.config.ts
└── next.config.ts
```

## Server vs Client Components

```tsx
// Server Component (по умолчанию) — data fetching, no interactivity
export default async function ItemsPage() {
  const items = await fetchItems()  // прямой fetch на сервере
  return <ItemList items={items} />
}

// Client Component — интерактивность, хуки, события
"use client"
import { useState } from "react"

export function ItemForm({ onSubmit }: Props) {
  const [name, setName] = useState("")
  return <form onSubmit={() => onSubmit(name)}>...</form>
}
```

**Правило:** Server Component по умолчанию. `"use client"` только когда нужны: useState, useEffect, onClick, onChange, browser APIs.

## shadcn/ui

```bash
npx shadcn@latest add button card dialog input
```

```tsx
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

<Card className="dark:bg-zinc-900">
  <CardHeader>
    <CardTitle>Заголовок</CardTitle>
  </CardHeader>
  <CardContent>
    <Button variant="default" size="sm">Действие</Button>
  </CardContent>
</Card>
```

## API клиент

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(error.error ?? "API Error")
  }
  return res.json()
}
```

## Тёмная тема

```css
/* globals.css */
@layer base {
  :root { --background: 0 0% 100%; --foreground: 0 0% 3.9%; }
  .dark { --background: 0 0% 3.9%; --foreground: 0 0% 98%; }
}
```

```tsx
// layout.tsx
<html lang="ru" className="dark">
```

## Чеклист

- [ ] Server Components по умолчанию
- [ ] `"use client"` только для интерактивности
- [ ] shadcn/ui для UI-компонентов
- [ ] Тёмная тема через CSS variables
- [ ] API через fetch обёртку, не axios
- [ ] Типы в `types/`, не inline
- [ ] `loading.tsx` для Suspense
