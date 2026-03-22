# Аудит проекта Aether (Эфир)

Дата: 2026-03-20

---

## 1. Структура проекта (src/ — 73 файла)

```
src/
├── main.tsx                              5 строк
├── App.tsx                              80 строк
├── vite-env.d.ts                         1
├── components/
│   ├── artifacts/
│   │   ├── ArtifactTabs.tsx             57
│   │   ├── ArtifactViewer.tsx          109
│   │   ├── GenerateArtifactPanel.tsx   342
│   │   └── views/
│   │       ├── DevelopmentView.tsx      378
│   │       ├── GlossaryView.tsx        124
│   │       ├── ProtocolView.tsx        149
│   │       ├── QuestionsView.tsx       138
│   │       ├── RawTextView.tsx          11
│   │       ├── RequirementsView.tsx    164
│   │       ├── RisksView.tsx           159
│   │       ├── SummaryView.tsx         314
│   │       ├── TranscriptView.tsx      139
│   │       └── shared.tsx              155
│   ├── audio/
│   │   └── WaveformPlayer.tsx          250
│   ├── glass/
│   │   ├── GlassButton.tsx              75
│   │   ├── GlassCard.tsx                40
│   │   ├── GlassInput.tsx               48
│   │   ├── GlassModal.tsx               63
│   │   ├── GlassPanel.tsx               14
│   │   ├── GlassToast.tsx               70
│   │   └── index.ts                      6
│   ├── layout/
│   │   ├── AppLayout.tsx                17
│   │   ├── BackgroundBlobs.tsx          52
│   │   └── Sidebar.tsx                 177
│   ├── pipeline/
│   │   ├── ArtifactProgress.tsx         88
│   │   ├── PipelineStages.tsx           81
│   │   ├── StageIndicator.tsx           85
│   │   └── StreamingText.tsx            60
│   ├── shared/
│   │   ├── AnimatedPage.tsx             21
│   │   ├── EmptyState.tsx               26
│   │   ├── LoadingSpinner.tsx           25
│   │   └── NewProjectModal.tsx         138
│   └── upload/
│       ├── DragDropZone.tsx            337
│       └── FileCard.tsx                 67
├── hooks/
│   └── useSound.ts                      21
├── lib/
│   ├── chunking.ts                     128
│   ├── constants.ts                    210
│   ├── cost-estimator.ts               140
│   ├── prompts.ts                      343
│   ├── provider-router.ts             140
│   ├── rate-limiter.ts                 138
│   ├── schemas.ts                      114
│   └── validators.ts                   193
├── pages/
│   ├── DashboardPage.tsx               193
│   ├── GuidePage.tsx                   498
│   ├── OnboardingPage.tsx              249
│   ├── PipelinePage.tsx                698
│   ├── ProjectPage.tsx                 359
│   ├── ProjectsListPage.tsx            125
│   ├── SettingsPage.tsx                325
│   ├── TemplatesPage.tsx               420
│   └── ViewerPage.tsx                  373
├── services/
│   ├── export.service.ts               794
│   ├── file-storage.service.ts          76
│   ├── file.service.ts                 133
│   ├── keys.service.ts                 181
│   ├── llm.service.ts                  518
│   ├── pipeline.service.ts             692
│   ├── sound.service.ts                 85
│   └── whisper.service.ts              453
├── stores/
│   ├── artifacts.store.ts              102
│   ├── pipeline.store.ts              179
│   ├── projects.store.ts               64
│   ├── settings.store.ts               79
│   └── ui.store.ts                      43
├── styles/
│   └── globals.css                     156
└── types/
    ├── api.types.ts                     43
    ├── artifact.types.ts               249
    ├── pipeline.types.ts                49
    └── project.types.ts                 25
```

**Итого:** ~10,500+ строк кода, 73 файла
**Крупнейшие файлы:** export.service.ts (794), PipelinePage.tsx (698), pipeline.service.ts (692)

---

## 2. package.json

```json
{
  "name": "aether",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "tauri": "tauri",
    "audit": "npm audit"
  },
  "dependencies": {
    "@tauri-apps/api": "^2",
    "@tauri-apps/plugin-dialog": "^2.6.0",
    "@tauri-apps/plugin-opener": "^2",
    "@tauri-apps/plugin-sql": "^2.3.2",
    "@tauri-apps/plugin-stronghold": "^2.3.1",
    "docx": "^9.6.1",
    "file-saver": "^2.0.5",
    "howler": "^2.2.4",
    "jszip": "^3.10.1",
    "motion": "^12.36.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-router-dom": "^7.13.1",
    "zod": "^3.23.8",
    "zustand": "^5.0.11"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.2.1",
    "@tauri-apps/cli": "^2",
    "@types/file-saver": "^2.0.7",
    "@types/howler": "^2.2.12",
    "@types/react": "^19.1.8",
    "@types/react-dom": "^19.1.6",
    "@vitejs/plugin-react": "^4.6.0",
    "tailwindcss": "^4.2.1",
    "typescript": "~5.8.3",
    "vite": "^7.0.4"
  }
}
```

**Dependencies:** 14 | **DevDependencies:** 10

---

## 3. tauri.conf.json

```json
{
  "productName": "Aether",
  "version": "0.1.0",
  "identifier": "com.aether.app",
  "build": {
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:1421",
    "beforeBuildCommand": "npm run build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [{
      "title": "Aether — Эфир",
      "width": 1280, "height": 800,
      "minWidth": 1024, "minHeight": 768,
      "center": true, "decorations": true,
      "resizable": true, "dragDropEnabled": true
    }],
    "security": {
      "csp": "...connect-src 'self' https://api.openai.com https://api.anthropic.com"
    }
  },
  "bundle": {
    "targets": ["nsis"],
    "windows": {
      "nsis": {
        "installMode": "currentUser",
        "languages": ["Russian"]
      }
    }
  }
}
```

---

## 4. Cargo.toml (Rust backend)

```toml
[package]
name = "aether"
version = "0.1.0"
edition = "2021"

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-opener = "2"
tauri-plugin-stronghold = "2"
tauri-plugin-dialog = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
reqwest = { version = "0.12", features = ["multipart", "json"] }
tokio = { version = "1", features = ["full"] }
rust-argon2 = "1.0"
```

---

## 5. Stores (Zustand)

### artifacts.store.ts (102 строк)
- 3 preset-шаблона: full-package (7 типов), quick-protocol (3), survey (4)
- 7+1 типов артефактов: protocol, requirements, risks, glossary, questions, transcript, development, summary
- Миграция v2: обновляет пресеты, сохраняет кастомные
- `toggleArtifact()`, `setActiveTemplate()`, `resetToDefault()`

### pipeline.store.ts (179 строк)
- 5 этапов: upload → extract → transcribe → generate → complete
- `fileStatuses: Map<fileName, FileProcessingStatus>`
- Partialize: persist только meetingId, stages, progress, currentStage
- `setStage()`, `setFileStatus()`, `resetPipeline()`, `setError()`

### projects.store.ts (64 строки)
- CRUD: `addProject()`, `updateProject()`, `deleteProject()`
- Встречи: `addMeeting()`, `updateMeeting()`
- Persist middleware (localStorage)

### settings.store.ts (79 строк)
- 9 API-ключей: openai, anthropic, groq, deepseek, gemini, mimo, cerebras, mistral, openrouter
- Ключи НЕ persist-ятся (partialize исключает apiKeys)
- `loadKeys()` → загрузка из Tauri Stronghold при старте
- `saveKey(provider, value)` → сохранение в Stronghold

### ui.store.ts (43 строки)
- `sidebarCollapsed`, `loading`, `toasts[]`
- `addToast()` с auto-dismiss (5 секунд)
- `removeToast()`, `setLoading()`, `toggleSidebar()`

---

## 6. Роутинг (App.tsx, 80 строк)

```
BrowserRouter → AnimatePresence → Routes → AppLayout
├── /                   → DashboardPage
├── /projects           → ProjectsListPage
├── /projects/:id       → ProjectPage
├── /pipeline           → PipelinePage
├── /viewer             → ViewerPage
├── /templates          → TemplatesPage
├── /guide              → GuidePage
├── /settings           → SettingsPage
└── *                   → Navigate → /
```

**Onboarding gate:** если `!onboardingCompleted` → показывает только OnboardingPage
**Init:** soundService.init(), loadKeys(), очистка прерванного pipeline

---

## 7. Сервисы

### whisper.service.ts (453 строки)
- **Мульти-провайдер STT:** OpenAI Whisper, Groq Whisper, Gemini (multimodal)
- **Fallback chain:** preferred → groq → gemini → openai
- **Tauri backend:** `invoke('call_whisper_compatible_api')` в production, direct fetch в dev
- **Retry:** MAX_RETRIES=2, delays [5s, 15s], timeout 5 мин
- **Quality analysis:** avgNoSpeechProb, avgLogProb, lowQualityPercent
- **WhisperError** class с типизированными кодами

### llm.service.ts (518 строк)
- 9 LLM-провайдеров: claude, openai, gemini, groq, deepseek, mimo, cerebras, mistral, openrouter
- Streaming responses
- Provider routing с fallback

### pipeline.service.ts (692 строки)
- Полный pipeline: upload → extract → transcribe → generate → complete
- Координация whisper + llm + артефакты
- File-level tracking

### export.service.ts (794 строки)
- Экспорт в DOCX (через docx library)
- Экспорт в ZIP (через jszip)
- Формирование структурированных документов

### sound.service.ts (85 строк)
- Web Audio API синтетические звуки (6 типов)
- Single AudioContext паттерн

### keys.service.ts (181 строка)
- Tauri Stronghold интеграция
- CRUD для API-ключей

### file.service.ts (133 строки)
- Работа с файлами через Tauri Dialog API

### file-storage.service.ts (76 строк)
- Локальное хранение файлов

---

## 8. Дизайн-система "Aether Glass"

### globals.css (156 строк)
- **Тема:** только светлая (light glassmorphism)
- **Фон:** градиент #F0F4FF → #E8EEFF + анимированные blob-ы
- **Стекло:** `.glass` (blur 12px), `.glass-subtle` (blur 8px), `.glass-strong` (blur 16px)
- **Акцент:** индиго #6C5CE7, бирюзовый #00CEC9
- **Шрифт:** Inter (основной), JetBrains Mono (код/таймкоды)
- **Звуки:** 6 типов (click, navigate, upload, start, success, error)

### Glass-компоненты
- GlassButton (75) — кнопка с variants: primary/secondary/ghost/danger
- GlassCard (40) — карточка с backdrop-filter
- GlassInput (48) — инпут со стеклянным стилем
- GlassModal (63) — модальное окно
- GlassPanel (14) — панель
- GlassToast (70) — уведомления

---

## 9. Типы

### artifact.types.ts (249 строк)
- 8 ArtifactType: protocol, requirements, risks, glossary, questions, transcript, development, summary
- `Artifact`, `ArtifactTemplate`, `ArtifactPreset` интерфейсы
- `ARTIFACT_DESCRIPTIONS` — детальная документация по каждому типу
- `DevTask` типы для development-артефакта

### api.types.ts (43 строки)
- 9 LLM-провайдеров, 3 STT-провайдера
- `ProviderRoutingMode`, `DEFAULT_SETTINGS`

### pipeline.types.ts (49 строк)
- `PipelineStage`, `StageStatus`, `FileProcessingStatus`

### project.types.ts (25 строк)
- `Project`, `Meeting` интерфейсы

---

## 10. Билд

```
> tsc && vite build
vite v7.0.4 building client environment for production...
✓ 541 modules transformed.
✓ built in 5.29s

dist/assets/index-xxx.css     52.89 kB │ gzip: 10.36 kB
dist/assets/vendor-docx.js   440.74 kB │ gzip: 99.58 kB
dist/assets/vendor-motion.js  93.60 kB │ gzip: 35.07 kB
dist/assets/index-xxx.js     587.91 kB │ gzip: 151.68 kB
```

**Билд: OK** — 541 модулей, 5.29 секунд
**Предупреждений:** 1 (dynamic import @tauri-apps/api/core.js — норма для Tauri)
**Ошибок:** 0
**Общий вес:** ~1.17 MB (296 kB gzip)

---

## 11. Резюме

| Параметр | Значение |
|----------|----------|
| **Стек** | Tauri 2.x + React 19 + TypeScript 5.8 + Vite 7 |
| **Стили** | Tailwind CSS 4 + glassmorphism (light theme) |
| **State** | Zustand 5 (5 stores, persist middleware) |
| **Роутинг** | React Router 7 (9 маршрутов) |
| **Анимации** | Motion (ex-Framer Motion) |
| **AI** | 9 LLM + 3 STT провайдеров с fallback |
| **Безопасность** | API-ключи в Tauri Stronghold |
| **Экспорт** | DOCX + ZIP |
| **Звук** | Web Audio API (синтетические) |
| **Файлов** | 73 (src/) |
| **Строк кода** | ~10,500+ |
| **Билд** | OK (5.29s, 0 ошибок) |
| **Installer** | NSIS (Windows, currentUser) |
