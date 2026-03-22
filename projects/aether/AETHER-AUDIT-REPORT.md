# Aether — Полный аудит проекта
Дата: 2026-03-20

## TL;DR

Aether — десктопное Tauri-приложение для транскрипции встреч и генерации AI-артефактов. Главное преимущество перед конкурентами — мультипровайдерность (9 LLM с fallback) и структурированные артефакты. Бандл 1.17 MB — отличный результат. Архитектура в целом здоровая: immutable state, retry/fallback, crash recovery. Однако приложение **не работает в production-сборке** для 6 из 9 провайдеров из-за неполной CSP и рассинхронизированных Zod-схем. Тема — только светлая, что противоречит позиционированию как премиальный продукт на рынке, где тёмная тема — стандарт.

## Позиция на рынке

**Уникальное у Aether:**
- AI-артефакты из транскрипции (протокол, требования, риски, глоссарий, вопросы, стенограмма, ТЗ) — нет ни у одного конкурента
- 9 LLM-провайдеров с auto-routing и fan-out — уникально среди десктопных решений
- Бандл 1.17 MB — легчайший среди всех (Electron-аналоги 100-250 MB)
- Dark Glassmorphism + Gold/Amber палитра (когда будет реализована) — уникальный стиль

**Главный конкурент: [Vibe](https://github.com/thewh1teagle/vibe)** — тот же стек (Tauri + TS + Rust), 5.6k stars, 37 контрибьюторов, GPU-ускорение, Claude API. Дифференциация Aether = AI-артефакты + мультипровайдерность + дизайн.

**Стоит добавить:** Speaker Diarization (высокий приоритет), Waveform+текст синхронизация, Batch processing, Keyboard shortcuts.

**Не стоит добавлять:** CRM-интеграции, Zoom/Teams-бот, подписочная модель, веб-версия.

## Критические проблемы (P0)

### P0-1: Неполная проверка STT/LLM-ключей
- **Файл:** `src/pages/PipelinePage.tsx`, строки 159–171
- **Суть:** `sttKeyMap` содержит только `groq`. При выборе `openai`/`gemini` как STT-провайдер, fallback всегда `groqKey` — проверка пройдёт даже без нужного ключа, пайплайн сломается позже. Аналогично для `llmKeyMap` — нет `claude` и `openai`.
- **Исправление:** заменить на полные карты, аналогичные `LLM_KEY_MAP`/`STT_KEY_MAP` из `pipeline.service.ts`.

### P0-2: Zod-схемы не покрывают все провайдеры
- **Файл:** `src/lib/schemas.ts`, строки 43–44
- **Суть:** `LLMProviderSchema` не содержит `cerebras`, `mistral`, `openrouter`. `STTProviderSchema` не содержит `gemini`. Выбор этих провайдеров тихо блокирует запуск пайплайна без понятного сообщения.
- **Исправление:** синхронизировать с типами из `src/types/api.types.ts`.

### P0-3: CSP блокирует 6 из 9 LLM-провайдеров в production
- **Файл:** `src-tauri/tauri.conf.json`, строка 27
- **Суть:** `connect-src` содержит только `api.openai.com` и `api.anthropic.com`. Отсутствуют: `api.groq.com`, `generativelanguage.googleapis.com`, `api.deepseek.com`, `api.xiaomimimo.com`, `api.cerebras.ai`, `api.mistral.ai`, `openrouter.ai`. Также нет `blob:` для audio blob. В dev-режиме работает через Vite proxy — баг невидим при разработке.
- **Исправление:** добавить все домены провайдеров в `connect-src`, добавить `blob:`.

## Серьёзные проблемы (P1)

### P1-1: Нет proxy для 3 провайдеров в Vite
- **Файл:** `vite.config.ts`
- Proxy отсутствует для `cerebras`, `mistral`, `openrouter` — в dev-режиме без Tauri окна будут CORS-ошибки.

### P1-2: GenerateArtifactPanel не передаёт транскрипцию
- **Файл:** `src/components/artifacts/GenerateArtifactPanel.tsx`
- Генерация артефакта вызывается без исходных данных транскрипции — артефакт генерируется "вслепую".

### P1-3: storeAudioFile() нигде не вызывается
- **Файл:** `src/services/file-storage.service.ts`
- Функция определена, но не вызывается в PipelinePage. Сценарий "возобновить обработку" работает только через blob URL в рамках одной сессии.

### P1-4: StreamingText накапливается без лимита
- **Файл:** `src/stores/pipeline.store.ts`, строка 102
- Строка неограниченно растёт, может накапливать десятки KB в localStorage.

### P1-5: Двойная валидация файлов
- **Файл:** `src/services/pipeline.service.ts`, строки 209–227
- Файлы валидируются дважды: в цикле (строка 209) и через повторный вызов (строка 225).

### P1-6: Навигация перегружена — 7 пунктов вместо 4–5
- **Файл:** `src/components/layout/Sidebar.tsx`
- "Главная" дублирует DragDropZone, "Справка" и "Шаблоны" занимают место в основной навигации необоснованно.

### P1-7: Только светлая тема — не соответствует позиционированию
- **Файлы:** `src/styles/globals.css`, glass-компоненты
- Фон `#F0F4FF`, поверхности `rgba(255,255,255,...)`. Нет `dark:` утилит, нет `prefers-color-scheme`. Все конкуренты (Vibe, MacWhisper, Voibe) используют тёмную тему.

---

## План "от А до Я за одну сессию"

### Фаза 1 — Стабилизация (2–3 часа)

- [ ] **P0-2: Синхронизировать Zod-схемы** — `src/lib/schemas.ts`: добавить `cerebras`, `mistral`, `openrouter` в `LLMProviderSchema`, `gemini` в `STTProviderSchema`
- [ ] **P0-3: Исправить CSP** — `src-tauri/tauri.conf.json`: добавить все домены провайдеров в `connect-src` + `blob:`
- [ ] **P0-1: Полные карты ключей** — `src/pages/PipelinePage.tsx`: заменить `sttKeyMap` и `llmKeyMap` на полные карты из `pipeline.service.ts`, либо импортировать из `src/lib/constants.ts`
- [ ] **P1-1: Добавить Vite proxy** — `vite.config.ts`: добавить proxy для `cerebras`, `mistral`, `openrouter`
- [ ] **P1-2: Передать транскрипцию в GenerateArtifactPanel** — `src/components/artifacts/GenerateArtifactPanel.tsx`: передавать текст транскрипции при вызове `generateArtifact()`
- [ ] **P1-3: Вызвать storeAudioFile()** — `src/pages/PipelinePage.tsx`: вызывать `storeAudioFile()` при создании встречи для persistence
- [ ] **P1-4: Лимит StreamingText** — `src/stores/pipeline.store.ts`: ограничить длину строки (например, последние 10 000 символов)
- [ ] **P1-5: Убрать дублирование валидации** — `src/services/pipeline.service.ts`: удалить повторный вызов `validateAudioFile()` на строке 225

### Фаза 2 — Тёмная тема Dark Gold/Amber (3–4 часа)

- [ ] **Замена CSS-токенов** — `src/styles/globals.css`: фон `#1A1A1E`, поверхности с тёмной основой, акценты `#C8A050` (золото) и `#E08040` (амбер)
- [ ] **Glass-компоненты** — `src/components/glass/GlassButton.tsx`, `GlassCard.tsx`, `GlassInput.tsx`, `GlassPanel.tsx`: заменить hardcoded `rgba(255,255,255,...)` на тёмные варианты
- [ ] **BackgroundBlobs** — `src/components/layout/BackgroundBlobs.tsx`: заменить светлые blob-цвета на тёмные приглушённые
- [ ] **Sidebar** — `src/components/layout/Sidebar.tsx`: адаптировать под тёмную палитру
- [ ] **Все страницы** — пройти по всем `src/pages/*.tsx` и заменить hardcoded светлые цвета (border, bg, text)
- [ ] **Тестирование контраста** — проверить WCAG AA для всех текстов на тёмном фоне

### Фаза 3 — Производительность (1–2 часа)

- [ ] **Lazy loading роутов** — `src/App.tsx`: обернуть ViewerPage, PipelinePage, SettingsPage, TemplatesPage, GuidePage в `React.lazy()` + `Suspense`
- [ ] **Динамический импорт docx** — `src/services/export.service.ts`: `const { Document } = await import('docx')` при первом экспорте (экономия ~400 KB при старте)
- [ ] **React.memo для views** — `src/components/artifacts/views/ProtocolView.tsx`, `RequirementsView.tsx` и остальные: обернуть в `React.memo`
- [ ] **Удалить @tauri-apps/plugin-sql** — `package.json`: удалить неиспользуемую зависимость (~50 KB)
- [ ] **useCallback в PipelinePage** — `src/pages/PipelinePage.tsx`, строка 376: разбить 14-зависимый dep array на отдельные хуки

### Фаза 4 — UX улучшения (2–3 часа)

- [ ] **Упростить сайдбар до 4–5 пунктов** — `src/components/layout/Sidebar.tsx`: убрать "Справка" (перенести иконкой "?" вниз), убрать "Шаблоны" (inline в PipelinePage)
- [ ] **Встроить выбор шаблона в PipelinePage** — `src/pages/PipelinePage.tsx`: inline-селектор или drawer вместо отдельной страницы
- [ ] **Распределить контент GuidePage** — `src/pages/GuidePage.tsx`: описания артефактов → tooltips в PipelinePage, советы по аудио → hint в DragDropZone, рабочий процесс → в онбординг
- [ ] **Горизонтальный stepper прогресса** — `PipelineStages` компонент: заменить вертикальный список на горизонтальный stepper (как у MacWhisper/Vibe)
- [ ] **Онбординг: ссылки на получение ключей** — `src/pages/OnboardingPage.tsx`: добавить ссылку на console.groq.com, упомянуть приватность на шаге 1
- [ ] **Settings: переупорядочить** — `src/pages/SettingsPage.tsx`: порядок: API-ключи → Провайдеры → Маршрутизация → Звук
- [ ] **ViewerPage: breadcrumb** — `src/pages/ViewerPage.tsx`: добавить "← Все встречи" при просмотре артефактов
- [ ] **DragDropZone: touch targets** — `src/components/upload/DragDropZone.tsx`: увеличить кнопки ▲/▼ до минимум 44px

### Фаза 5 — Новые фичи (опционально, 4–6 часов)

- [ ] **Speaker Diarization** — цветовое кодирование спикеров, переименование "Speaker 1" → "Иван Петров" (высокий приоритет, есть у Buzz/Vibe/Otter)
- [ ] **Waveform + текст синхронизация** — `src/components/audio/WaveformPlayer.tsx` + `ViewerPage.tsx`: клик по waveform → курсор на тексте, выделение текста → подсветка на waveform
- [ ] **Batch processing** — очередь файлов с индивидуальным прогрессом
- [ ] **Keyboard shortcuts** — Play/Pause, Jump, Split, Merge без мыши, кастомизируемые хоткеи
- [ ] **Множественные форматы экспорта** — добавить SRT, VTT, PDF, HTML (сейчас DOCX + TXT + JSON)

---

## Что убрать совсем

| Что | Файл | Обоснование |
|-----|------|-------------|
| `ArtifactTabs.tsx` | `src/components/artifacts/ArtifactTabs.tsx` | Мёртвый компонент — нигде не импортируется, ViewerPage реализует табы inline |
| `pickBestProvider()` | `src/lib/provider-router.ts` | Экспортируется, но нигде не импортируется — мёртвый код |
| `@tauri-apps/plugin-sql` | `package.json` | Установлен, но в коде нет ни одного импорта. Лишние ~50 KB |
| GuidePage из сайдбара | `src/components/layout/Sidebar.tsx` | Контент полезный, но отдельная страница в основной навигации — неправильное место. Распределить по tooltips/hints |
| TemplatesPage из сайдбара | `src/components/layout/Sidebar.tsx` | Встроить как inline-селектор в PipelinePage |
| Дублирование `LLM_KEY_MAP` | `PipelinePage.tsx`, `pipeline.service.ts`, `provider-router.ts`, `settings.store.ts` | Вынести в единый источник `src/lib/constants.ts` |

## Что оставить как есть

| Что | Обоснование |
|-----|-------------|
| **Stronghold для API-ключей** (`keys.service.ts`) | Корректная реализация: шифрованный vault, ключи исключены из localStorage persist, dev-fallback через sessionStorage |
| **Immutable Zustand stores** | Все операции через spread — мутаций нет |
| **Retry + Fallback в llm.service.ts и whisper.service.ts** | Правильный паттерн: retry с backoff, автопереключение провайдеров, partial success сохраняется |
| **JSON auto-repair** (`validators.ts`) | 3-попытки парсинга с очисткой markdown, trailing commas, незакрытых скобок — работает |
| **Chunking для длинных транскриптов** (`lib/chunking.ts`) | Map-Reduce объединение — корректно |
| **AbortController в пайплайне** | Отмена поддерживается, прерванные встречи помечаются как `error` |
| **Auto-routing с fan-out** (`provider-router.ts`) | Параллельное распределение артефактов по провайдерам — до 4x ускорение |
| **Кумулятивный контекст** | Предыдущие артефакты передаются в промпт — умная функция |
| **Pipeline crash recovery** | `App.tsx` проверяет прерванный пайплайн при старте |
| **validateArtifactSchema** | Правильно разделяет `valid` и `isEmpty` |
| **DragDropZone** (`DragDropZone.tsx`) | Хорошо разделяет Tauri/web, multi-file, drag-reorder |
| **ArtifactViewer** (`ArtifactViewer.tsx`) | Чистый switch-компонент, 110 строк, правильная архитектура |
| **Бандл 1.17 MB** | Отличный результат для Tauri-приложения |

## Оценка времени

| Этап | Часы |
|------|------|
| Фаза 1 — Стабилизация (P0 + P1) | 2–3 |
| Фаза 2 — Тёмная тема | 3–4 |
| Фаза 3 — Производительность | 1–2 |
| Фаза 4 — UX улучшения | 2–3 |
| Фаза 5 — Новые фичи | 4–6 |
| **Минимум для рабочего MVP:** | **5–7 часов** (Фазы 1 + 2) |
| **Полный редизайн + оптимизация:** | **12–18 часов** (Фазы 1–5) |
