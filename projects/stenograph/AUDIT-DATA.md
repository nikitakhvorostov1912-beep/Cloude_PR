# Аудит проекта Stenograph (Эфир)

Дата: 2026-03-20

---

## 1. Структура проекта (2 уровня)

```
stenograph/
├── .gitignore
├── README.md
├── eslint.config.js
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
├── node_modules/
├── public/
│   ├── favicon.svg
│   └── icons.svg
├── src/
│   ├── App.css
│   ├── App.tsx
│   ├── index.css
│   ├── main.tsx
│   └── assets/
│       ├── hero.png
│       ├── react.svg
│       └── vite.svg
└── dist/  (после билда)
```

**Нет:**
- src-tauri/ — НЕТ Tauri (чистый Vite + React)
- src/stores/ — НЕТ
- src/components/ — НЕТ
- src/pages/ — НЕТ
- src/services/ — НЕТ
- src/types/ — НЕТ
- CLAUDE.md — НЕТ

---

## 2. package.json

```json
{
  "name": "stenograph",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.2.4",
    "react-dom": "^19.2.4"
  },
  "devDependencies": {
    "@eslint/js": "^9.39.4",
    "@types/node": "^24.12.0",
    "@types/react": "^19.2.14",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.0",
    "eslint": "^9.39.4",
    "eslint-plugin-react-hooks": "^7.0.1",
    "eslint-plugin-react-refresh": "^0.5.2",
    "globals": "^17.4.0",
    "typescript": "~5.9.3",
    "typescript-eslint": "^8.56.1",
    "vite": "^8.0.0"
  }
}
```

**Dependencies:** 2 (react, react-dom)
**DevDependencies:** 10

---

## 3. Файлы в src/ с размерами

| Файл | Строк | Тип |
|------|-------|-----|
| src/main.tsx | 10 | Точка входа |
| src/App.tsx | 121 | Единственный компонент |
| src/App.css | 184 | Стили компонента |
| src/index.css | 111 | Глобальные стили |
| src/assets/hero.png | — | Изображение (бинарный) |
| src/assets/react.svg | 0 (пустой) | SVG логотип |
| src/assets/vite.svg | 1 | SVG логотип |

**Итого кода:** 426 строк (4 файла .tsx/.css)

---

## 4. Ключевые файлы

### src/main.tsx (10 строк)
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

### src/App.tsx (121 строк)
Стандартный шаблон Vite: hero-секция с логотипами React/Vite, счётчик (useState), секции Documentation и Connect with us со ссылками на vite.dev, react.dev, GitHub, Discord, X, Bluesky.

**Кастомной логики нет.** Это дефолтный `npm create vite@latest` шаблон.

### vite.config.ts (7 строк)
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
```
Минимальный — без алиасов, proxy, настроек.

### index.html (13 строк)
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>stenograph</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### tsconfig.json (7 строк)
Ссылочный — два конфига: tsconfig.app.json + tsconfig.node.json

### index.css (111 строк)
CSS-переменные для light/dark тем. Vite-стандартная палитра:
- Light: белый фон, фиолетовый акцент (#aa3bff)
- Dark: тёмный фон (#16171d), фиолетовый акцент (#c084fc)

### App.css (184 строк)
Стили hero-секции, счётчика, документации, social-ссылок. CSS nesting, responsive (1024px breakpoint).

### Stores — НЕТ
### Components — НЕТ (всё в App.tsx)
### Pages — НЕТ (SPA без роутинга)

---

## 5. Билд

```
> stenograph@0.0.0 build
> tsc -b && vite build

vite v8.0.0 building client environment for production...
✓ 20 modules transformed.
✓ built in 161ms
```

**Билд: OK** — без ошибок, без предупреждений.

---

## 6. Размер бандла (dist/)

| Файл | Размер | gzip |
|------|--------|------|
| dist/index.html | 0.47 kB | 0.30 kB |
| dist/assets/react-CHdo91hT.svg | 4.12 kB | 2.06 kB |
| dist/assets/vite-BF8QNONU.svg | 8.70 kB | 1.60 kB |
| dist/assets/hero-5sT3BiRD.png | 44.91 kB | — |
| dist/assets/index-D64VDMd1.css | 4.10 kB | 1.47 kB |
| dist/assets/index-Bc2oaLMj.js | 193.32 kB | 60.66 kB |

**Общий вес:** ~255 kB (66 kB gzip)
**JS бандл:** 193 kB — это React + ReactDOM (кастомного кода ~0)

---

## 7. Резюме состояния

| Параметр | Значение |
|----------|----------|
| **Шаблон** | `npm create vite@latest` (React + TypeScript) |
| **Кастомный код** | 0 строк (всё дефолтное) |
| **Роутинг** | Нет |
| **State management** | Нет (один useState) |
| **Tauri** | Нет |
| **Тесты** | Нет |
| **CLAUDE.md** | Нет |
| **Стек** | React 19.2 + Vite 8.0 + TypeScript 5.9 |
| **Билд** | OK |
| **README** | Дефолтный Vite template README |
