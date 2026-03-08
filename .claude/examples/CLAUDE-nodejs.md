# {PROJECT_NAME}

## Стек
- Next.js 15 (App Router)
- React 19
- TypeScript (strict mode)
- shadcn/ui для компонентов
- Tailwind CSS 4
- TanStack Query для кэширования API

## Правила кода

### Компоненты
- Все тексты интерфейса на русском языке
- Тёмная тема по умолчанию
- Server Components по умолчанию, `"use client"` только когда нужен state/effects
- Каждый UI элемент функционален (никаких заглушек)

### Структура
```
src/
├── app/           # Next.js App Router (pages, layouts)
├── components/    # UI компоненты
│   └── ui/        # shadcn/ui компоненты
├── hooks/         # Custom React hooks
├── lib/           # Утилиты, API клиент
└── types/         # TypeScript определения
```

### Стиль
- Именованные экспорты (не default)
- Интерфейсы вместо type aliases для объектов
- Функции < 50 строк, файлы < 400 строк
- `const` по умолчанию, `let` только при мутации
- Деструктуризация пропсов

## Тесты

```bash
npm run test
npm run build  # TypeScript проверка
```

## Запуск

```bash
cd {PROJECT_PATH}
npm install
npm run dev  # http://localhost:3000
```

## Перед коммитом
- `npm run build` — без ошибок TypeScript
- Нет `console.error` в браузере
- Проверить через Preview что UI работает
- Все тексты на русском
