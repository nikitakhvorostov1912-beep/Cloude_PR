# Aether (Эфир)

> Десктопное приложение для превращения аудио/видеозаписей встреч в структурированные проектные артефакты.

![Tauri](https://img.shields.io/badge/Tauri-2.x-blue?logo=tauri)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-4-38B2AC?logo=tailwindcss)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Что это?

**Aether** берёт запись вашей встречи (аудио или видео) и автоматически генерирует:

| Артефакт | Описание |
|----------|----------|
| **Протокол** | Повестка, решения, ответственные, дедлайны |
| **Требования** | Функциональные и нефункциональные требования |
| **Карта рисков** | Риски, вероятность, импакт, митигация |
| **Глоссарий** | Термины, определения, аббревиатуры |
| **Открытые вопросы** | Нерешённые вопросы, отложенные решения |
| **Стенограмма** | Форматированная расшифровка с таймкодами |

## Дизайн-система "Aether Glass"

Светлый glassmorphism с анимированными blob-ами на фоне, полупрозрачными стеклянными панелями и плавными переходами между страницами.

- Основной акцент: индиго `#6C5CE7`
- Второстепенный: бирюзовый `#00CEC9`
- Фон: мягкий градиент lavender mist
- Эффект стекла: `backdrop-filter: blur(12px)`
- Шрифты: Inter (основной), JetBrains Mono (код/таймкоды)
- 6 звуковых эффектов (отключаемые в настройках)

## Стек технологий

| Слой | Технология |
|------|-----------|
| Desktop | **Tauri 2.x** (Rust) — NSIS installer, ~2 MB |
| Frontend | **React 19** + **TypeScript 5.8** + **Vite 7** |
| Стили | **Tailwind CSS 4** + кастомный glassmorphism |
| Компоненты | Glass design system (GlassCard, GlassButton, GlassModal...) |
| Роутинг | **React Router 7** |
| Состояние | **Zustand 5** (persist middleware) |
| Анимации | **Motion** (ex-Framer Motion) |
| Звук | **Howler.js** + Web Audio API |
| AI: STT | **OpenAI Whisper API** |
| AI: LLM | **Claude** / **GPT-4** (выбор пользователя) |
| Экспорт | **docx** + **JSZip** (DOCX, ZIP) |

## Быстрый старт

### Требования

- **Node.js** 18+
- **Rust** 1.70+ (для Tauri)
- **Windows 10/11** с WebView2 (встроен в Win11)

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/nikitakhvorostov1912-beep/aether.git
cd aether

# Установить зависимости
npm install

# Запустить в режиме разработки (только фронтенд)
npm run dev

# Запустить как десктоп-приложение
npm run tauri dev
```

### Сборка инсталлятора

```bash
npm run tauri build
```

Результат: `src-tauri/target/release/bundle/nsis/Aether_0.1.0_x64-setup.exe`

## Структура проекта

```
aether/
├── src/
│   ├── components/
│   │   ├── glass/           # Glass UI: Card, Button, Input, Modal, Panel, Toast
│   │   ├── layout/          # AppLayout, Sidebar, BackgroundBlobs
│   │   ├── artifacts/       # ArtifactTabs, ArtifactViewer, 6 views
│   │   ├── pipeline/        # PipelineStages, StageIndicator, StreamingText
│   │   ├── upload/          # DragDropZone, FileCard
│   │   ├── audio/           # WaveformPlayer
│   │   └── shared/          # AnimatedPage, EmptyState, LoadingSpinner
│   ├── pages/               # 7 страниц приложения
│   │   ├── OnboardingPage   # Приветствие + ввод API-ключей
│   │   ├── DashboardPage    # Проекты + Drag & Drop загрузка
│   │   ├── ProjectPage      # Детали проекта + записи встреч
│   │   ├── PipelinePage     # 5-этапный AI-пайплайн
│   │   ├── ViewerPage       # Просмотр артефактов (6 табов)
│   │   ├── TemplatesPage    # Шаблоны (preset + custom CRUD)
│   │   └── SettingsPage     # Настройки, API-ключи, звук
│   ├── stores/              # Zustand stores (5 шт.)
│   ├── services/            # Whisper, LLM, Pipeline, Export, Sound, File
│   ├── lib/                 # AI-промпты, чанкинг, валидация, оценка стоимости
│   ├── hooks/               # useSound
│   ├── types/               # TypeScript типы
│   └── styles/              # Tailwind + glassmorphism токены
├── src-tauri/
│   ├── src/                 # Rust: Tauri entry + commands
│   ├── icons/               # Иконки приложения (все размеры)
│   ├── Cargo.toml
│   └── tauri.conf.json
├── public/
├── package.json
├── vite.config.ts
├── tsconfig.json
└── CLAUDE.md
```

## AI-пайплайн

```
  Загрузка файла
       │
  Извлечение аудио (ffmpeg)
       │
  Транскрипция (Whisper API)
       │
  ┌────┼────┬─────┬──────┬────────┐
  │    │    │     │      │        │
 Proto Req Risk Gloss Quest  Transcript
  │    │    │     │      │        │
  └────┴────┴─────┴──────┴────────┘
       │
  Сохранение + Экспорт (DOCX/ZIP)
```

Поддержка двух LLM-провайдеров: **Claude** (Anthropic) и **GPT-4** (OpenAI) — выбор в настройках.

## 7 экранов приложения

1. **Onboarding** — приветствие, ввод API-ключей, создание первого проекта
2. **Dashboard** — список проектов, Drag & Drop загрузка файлов
3. **Project** — детали проекта, записи встреч, waveform-плеер
4. **Pipeline** — визуализация 5 этапов обработки в реальном времени
5. **Viewer** — 6 табов артефактов, кликабельные таймкоды, экспорт DOCX
6. **Templates** — встроенные и пользовательские профили (CRUD)
7. **Settings** — API-ключи, выбор AI-провайдера, звук, о программе

## Glass UI компоненты

| Компонент | Описание |
|-----------|----------|
| `GlassCard` | Карточка с эффектом стекла, hover-анимация |
| `GlassButton` | Кнопка (primary / secondary / ghost / danger) |
| `GlassInput` | Поле ввода с лейблом и валидацией |
| `GlassModal` | Модальное окно с backdrop blur |
| `GlassPanel` | Боковая панель |
| `GlassToast` | Уведомления (success / error / info / warning) |

## Команды разработки

```bash
npm run dev          # Vite dev server (порт 1421)
npm run tauri dev    # Tauri окно с WebView2
npm run build        # Production build (tsc + vite)
npm run tauri build  # NSIS installer (.exe)
```

## Лицензия

MIT
