---
name: web-asset-generator
description: "Генерация web-ассетов: favicons, app icons, OG images из логотипа или текста. Используй когда нужно сгенерировать иконки для PWA, favicon для сайта, или картинки для соцсетей."
allowed-tools: Bash,Write,Read
---

# Web Asset Generator — Генератор веб-ассетов

Генерация профессиональных веб-ассетов: favicons, app icons (iOS/Android), Open Graph images из логотипа, эмоджи или текста.

> Источник: https://github.com/alonw0/web-asset-generator

## Когда использовать

- Нужен favicon для нового сайта
- Генерация app icons для PWA (192x192, 512x512)
- Создание OG images для Facebook, Twitter, LinkedIn
- Из логотипа → все размеры иконок одной командой
- Из эмоджи/текста → быстрые иконки для MVP

## Когда НЕ использовать

- Полноценный дизайн логотипа → используй `canvas-design`
- Анимированные ассеты → не поддерживается
- Фото-обработка → используй другие инструменты

## Требования

```bash
pip install Pillow cairosvg
```

## Три категории ассетов

### 1. Favicons
- `favicon.ico` (16x16, 32x32, 48x48 multi-size)
- `favicon-16x16.png`
- `favicon-32x32.png`
- `favicon-96x96.png`
- `apple-touch-icon.png` (180x180)

### 2. App Icons (PWA)
- `icon-192x192.png`
- `icon-512x512.png`
- `maskable-icon-512x512.png`
- `apple-touch-icon-180x180.png`

### 3. Social Media (OG Images)
- `og-image.png` (1200x630) — Facebook, LinkedIn
- `twitter-card.png` (1200x600) — Twitter/X
- `whatsapp-preview.png` (400x400)

## Скрипты

### generate_favicons.py
```python
"""Генерация favicon и app icons из логотипа или эмоджи.

Использование:
  python generate_favicons.py --source logo.png --output ./icons/
  python generate_favicons.py --emoji "🚀" --background "#1a1a2e" --output ./icons/
  python generate_favicons.py --text "AC" --background "#0066ff" --output ./icons/
"""
```

### generate_og_images.py
```python
"""Генерация OG images для социальных сетей.

Использование:
  python generate_og_images.py --logo logo.png --title "My App" --output ./og/
  python generate_og_images.py --text "Launch Day!" --background "#ff6b35" --output ./og/
"""
```

## Workflow

1. **Спросить пользователя** через AskUserQuestion:
   - Тип ассетов (favicon / app icons / OG images / все)
   - Источник (логотип / эмоджи / текст)
   - Цветовая схема

2. **Генерация**:
   ```bash
   python generate_favicons.py --source logo.png --output ./public/icons/
   python generate_og_images.py --logo logo.png --title "Название" --output ./public/
   ```

3. **Валидация** (опционально):
   ```bash
   python generate_favicons.py --source logo.png --output ./icons/ --validate
   # Проверяет: размеры, формат, WCAG контраст
   ```

4. **Интеграция** — определить фреймворк и предложить HTML:

### Next.js
```tsx
// app/layout.tsx
export const metadata = {
  icons: {
    icon: [
      { url: '/icons/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icons/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
    ],
    apple: '/icons/apple-touch-icon.png',
  },
  openGraph: {
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
  },
};
```

### Plain HTML
```html
<link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/icons/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png">
<meta property="og:image" content="/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
```

## Тестирование

- Facebook: [Sharing Debugger](https://developers.facebook.com/tools/debug/)
- Twitter: [Card Validator](https://cards-dev.twitter.com/validator)
- LinkedIn: [Post Inspector](https://www.linkedin.com/post-inspector/)
