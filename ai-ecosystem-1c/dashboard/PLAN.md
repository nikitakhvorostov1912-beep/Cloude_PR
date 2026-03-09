# План: Ребрендинг "Аврора" — Светлая тема + InterSoft палитра

## Концепция
Полная смена дизайн-системы со "Deep Ocean Aurora" (тёмная, teal) на "Аврора Light" (светлая, InterSoft palette).
Название системы: **Аврора**. Логотип: северное сияние в стиле IS-монограммы.

## Палитра InterSoft
| Роль | Цвет | HEX |
|------|------|-----|
| Primary (navy) | Тёмно-синий | #1C1475 |
| CTA (red) | Красный | #FF2124 |
| CTA hover | Тёмно-красный | #D10407 |
| Accent (blue) | Голубой | #7DBEF4 |
| Button navy | Кнопки | #190D78 |
| Background | Белый | #FFFFFF |
| Section bg | Серо-голубой | #EDF1F6 |
| Card bg | Светлый | #E5EBF2 |
| Text primary | Чёрный | #333333 |
| Text heading | Чёрный | #000000 |
| Text muted | Серый | #999999 |
| Gradient start | Фиолетовый | #EAE9FA |
| Gradient end | Розовый | #FCEFF5 |

## Шаги реализации

### Шаг 1: globals.css — Полная перезапись дизайн-системы
- Все цветовые токены → InterSoft palette
- Фон: #FFFFFF, секции: #EDF1F6
- Текст: #333333, #000000, #999999
- Borders: светло-серые (#E5EBF2, #DBDBDB)
- Surface: white glass (rgba(255,255,255,0.8) + blur)
- Aurora blobs: navy, red, blue, pink — очень низкая opacity (0.05-0.08) для светлого фона, больше blur
- Glass card: white bg + light shadow вместо тёмного glass
- Glow → subtle InterSoft shadows (box-shadow: 0 3px 14px #0000001c)
- Gradient text: navy→red (#1C1475→#FF2124)
- Floating dock: white frost glass
- Scrollbar: navy tones
- color-scheme: light

### Шаг 2: aurora-logo.tsx — Новый SVG логотип
- Абстрактная дуга северного сияния (3 кривых: navy, red, blue)
- Геометрический стиль IS-монограммы (sharp angles)
- Текст "Аврора" справа, Inter/Roboto, navy цвет
- Два размера: full (для header) и compact (для dock)

### Шаг 3: layout.tsx
- Убрать `className="dark"` с html
- Metadata title → "Аврора — Панель суфлёра"
- Всё остальное сохранить

### Шаг 4: aurora-background.tsx
- Blob цвета → navy, red, blue, pink-gradient
- Снизить opacity до 0.04-0.08 (на белом фоне нужно тоньше)
- Увеличить blur до 180px

### Шаг 5: particles.tsx
- Цвета → navy, blue (#7DBEF4), red, светло-серый
- Opacity чуть ниже для светлого фона

### Шаг 6: floating-dock.tsx
- Active: navy bg (bg-[#1C1475]/15, text-[#1C1475])
- Active dot: red (#FF2124)
- Tooltip: white bg, dark text, shadow

### Шаг 7: glow-card.tsx
- "teal" → "navy" (navy shadows)
- "orange" → "red" (InterSoft red shadows)
- Glare color: #7DBEF4
- Base glass: white bg + light border + shadow

### Шаг 8: kpi-card.tsx
- Accents: navy, blue, red, gradient
- Icon bg: navy/blue/red gradients

### Шаг 9: page.tsx (Dashboard)
- Заголовок: компонент AuroraLogo + "Панель управления • Суфлёр"
- Chart gradients: navy→blue вместо teal
- Dept chart colors: navy, red, blue, gradient-pink
- Tooltip: white glass
- Status colors: перевод на InterSoft palette

### Шаг 10: calls/page.tsx
- Search focus: navy border/shadow
- Row hover: navy-tinted
- Priority badges: InterSoft colors

### Шаг 11: live/page.tsx
- Header: navy icon
- Operator bubbles: navy-tinted
- CTA button: red gradient (#FF2124→#D10407)
- Form focus: navy border
- Recommendations: navy/blue

### Шаг 12: activity-feed.tsx + transcript-viewer.tsx
- call_in: blue (#7DBEF4)
- classified: navy (#1C1475)
- Operator bubbles: navy-tinted
- Tags: navy/blue

### Шаг 13: command-palette.tsx
- Dialog: white glass (bg-white/95)
- Search icon: navy
- Item hover: navy-tinted
- Footer: light bg

### Шаг 14: settings/page.tsx
- Тема: "Аврора Light"
- Продукт: "Аврора Суфлёр"
- Icon colors: navy instead of teal

### Шаг 15: Build + Verify
- npm run build
- Preview все 4 страницы
- Проверка console errors = 0
