# Aether (Эфир) — Desktop App

> Превращение аудио/видеозаписей встреч в структурированные проектные артефакты.

## Стек

- **Desktop:** Tauri 2.x (Rust) — NSIS installer для Windows
- **Frontend:** React 19 + TypeScript + Vite 7
- **Стили:** Tailwind CSS 4 + кастомный glassmorphism
- **Компоненты:** Glass design system (`src/components/glass/`)
- **Роутинг:** React Router 7
- **Состояние:** Zustand (persist middleware)
- **Анимации:** Motion (ex-Framer Motion)
- **Звук:** Howler.js + Web Audio API (синтетические звуки)
- **БД:** SQLite (tauri-plugin-sql)
- **AI:** OpenAI Whisper API + Claude/GPT-4

## Команды

```bash
npm run dev          # Vite dev server (порт 1421)
npm run tauri dev    # Tauri окно с WebView2
npm run build        # Production build
npm run tauri build  # NSIS installer
```

## Структура

```
src/
├── components/glass/    # GlassCard, GlassButton, GlassInput, GlassModal, GlassPanel, GlassToast
├── components/layout/   # AppLayout, Sidebar, BackgroundBlobs
├── components/shared/   # AnimatedPage, EmptyState, LoadingSpinner
├── pages/               # 7 страниц (Onboarding, Dashboard, Project, Pipeline, Viewer, Templates, Settings)
├── stores/              # 5 Zustand stores (settings, ui, projects, pipeline, artifacts)
├── services/            # sound.service (+ whisper, claude, openai, pipeline, export — итерации 2-4)
├── types/               # TypeScript типы
├── hooks/               # useSound (+ useProject, usePipeline — позже)
└── styles/globals.css   # Tailwind + glassmorphism токены
```

## Дизайн-система "Aether Glass"

- **Тема:** Только светлая (light glassmorphism)
- **Фон:** Градиент #F0F4FF → #E8EEFF + анимированные blob-ы
- **Стекло:** `backdrop-filter: blur(12px)` + полупрозрачные поверхности
- **Акцент:** Индиго #6C5CE7, бирюзовый #00CEC9
- **Шрифт:** Inter (основной), JetBrains Mono (код/таймкоды)
- **Звуки:** 6 типов (click, navigate, upload, start, success, error) — отключаемые

## Правила

- Все тексты на русском
- Каждый UI элемент функциональный (никаких заглушек)
- Glassmorphism обязателен: `.glass`, `.glass-subtle`, `.glass-strong`
- Анимации через Motion (page transitions, hover, tap)
- Immutable state (Zustand с persist)
- API-ключи хранить в Tauri Stronghold (не localStorage)

## AI-промпты

Источник: `docs/plans/stenograph-prompts.md` → порт в `src/lib/prompts.ts`
6 типов: протокол, требования, риски, глоссарий, вопросы, стенограмма

## Edge Cases

Источник: `docs/plans/stenograph-edge-cases.md`
31 edge case с приоритетами (MVP/Important/Later)
