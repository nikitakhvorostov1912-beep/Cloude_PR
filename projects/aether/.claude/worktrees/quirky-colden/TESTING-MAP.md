# Aether — Карта тестирования

> Дата: 2026-03-20
> Статус: ✅ 17 файлов, 296 тестов — все PASS
> Покрытие (focused modules): 85.87% stmts / 80.32% branches / 91.15% funcs / 85.93% lines

---

## Итоговая статистика

| Метрика | Значение | Порог |
|---------|----------|-------|
| Тест-файлы | 17 | — |
| Тестов всего | 296 | — |
| Passed | 296 | — |
| Failed | 0 | — |
| Statements | 85.87% | ≥70% ✅ |
| Branches | 80.32% | ≥70% ✅ |
| Functions | 91.15% | ≥70% ✅ |
| Lines | 85.93% | ≥70% ✅ |

---

## Покрытие по модулям

| Модуль | Stmts | Branches | Funcs | Lines |
|--------|-------|----------|-------|-------|
| `src/components/glass/` | 86.95% | 88.37% | 72.72% | 85.71% |
| `src/lib/` | 96.78% | 88.18% | 100% | 97.52% |
| `src/services/keys.service.ts` | ~46% | ~46% | ~46% | ~46% |
| `src/services/file.service.ts` | ~46% | ~46% | ~46% | ~46% |
| `src/stores/` | 98.14% | 96.66% | 97.43% | 97.46% |
| `src/types/api.types.ts` | 100% | 100% | 100% | 100% |

> Services coverage ниже из-за Tauri-специфичного кода (Stronghold-ветки недоступны в test-окружении).

---

## Тест-файлы

### Stores (5 файлов, ~83 теста)

| Файл | Тестируемый модуль | Тестов | Что проверяется |
|------|-------------------|--------|-----------------|
| `src/test/stores/ui.store.test.ts` | `src/stores/ui.store.ts` | 17 | Начальное состояние, toggleSidebar, setActiveRoute, addToast + 4s auto-remove (fake timers), removeToast, setLoading |
| `src/test/stores/pipeline.store.test.ts` | `src/stores/pipeline.store.ts` | 17 | Начальное состояние, startPipeline, setStage (прогресс, завершение предыдущих), setStageStatus, setProgress, appendStreamingText, setError, setEstimatedCost, resetPipeline |
| `src/test/stores/projects.store.test.ts` | `src/stores/projects.store.ts` | 18 | CRUD проектов и встреч, setActiveProject/Meeting, getProjectMeetings, каскадное удаление, updatedAt timestamp |
| `src/test/stores/artifacts.store.test.ts` | `src/stores/artifacts.store.ts` | 14 | 3 preset-шаблона при инициализации, addArtifact, getArtifactsByMeeting, getLatestArtifact (по версии), template CRUD, selectedTemplate |
| `src/test/stores/settings.store.test.ts` | `src/stores/settings.store.ts` | 17 | DEFAULT_SETTINGS, setLLMProvider, setSoundEnabled/Volume, setOnboardingCompleted, setApiKey (вызов saveApiKey), loadKeys (skip if loaded), hasValidKeys (разные провайдеры) |

### Library (6 файлов, ~125 тестов)

| Файл | Тестируемый модуль | Тестов | Что проверяется |
|------|-------------------|--------|-----------------|
| `src/test/lib/schemas.test.ts` | `src/lib/schemas.ts` | 28 | OpenAIKeySchema, ClaudeKeySchema, LLMParamsSchema (defaults, ranges), PipelineConfigSchema, AudioFileSchema, validatePipelineConfig, validateAudioFile |
| `src/test/lib/validators.test.ts` | `src/lib/validators.ts` | 30 | cleanLLMResponse (markdown stripping, BOM, JSON extraction), tryParseJSON (valid, markdown-wrapped, trailing comma, unclosed brackets, total fail), isEmptyArtifact (6 типов), validateArtifactSchema |
| `src/test/lib/chunking.test.ts` | `src/lib/chunking.ts` | 20 | estimateTokens, chunkTranscript (single chunk, multi-chunk, overlap), findBreakPoint (paragraph/line/sentence/space/hard), estimateChunking |
| `src/test/lib/cost-estimator.test.ts` | `src/lib/cost-estimator.ts` | 16 | estimateWhisperCost, estimateLLMCost (OpenAI + Anthropic, масштабирование), estimateTotalCost, estimateCostBeforeProcessing, formatCost |
| `src/test/lib/rate-limiter.test.ts` | `src/lib/rate-limiter.ts` | 14 | trackApiUsage (накопление, счётчик запросов), checkRateLimitWarnings (ниже/выше 80%), getDailyUsageSummary (нулевые значения, проценты) |
| `src/test/lib/prompts.test.ts` | `src/lib/prompts.ts` | 17 | buildPrompt (6 типов артефактов, температуры 0.1/0.3, project name/transcript в промпте, модификатор типа встречи), buildAllPrompts (6 типов, подмножество, пустой массив) |

### Services (2 файла, ~40 тестов)

| Файл | Тестируемый модуль | Тестов | Что проверяется |
|------|-------------------|--------|-----------------|
| `src/test/services/keys.service.test.ts` | `src/services/keys.service.ts` | 11 | Dev mode (sessionStorage): saveApiKey, loadApiKey, loadAllApiKeys (все ключи), deleteApiKey |
| `src/test/services/file.service.test.ts` | `src/services/file.service.ts` | 29 | isSupported (все форматы, регистронезависимость, неподдерживаемые), formatDuration (сек/мин/часы), revokeFileUrl (blob vs non-blob), processFile (бросает для неподдерживаемых форматов) |

### Components (4 файла, ~42 теста)

| Файл | Тестируемый модуль | Тестов | Что проверяется |
|------|-------------------|--------|-----------------|
| `src/test/components/GlassButton.test.tsx` | `src/components/glass/GlassButton.tsx` | 12 | Рендер, onClick, disabled state, loading spinner, icon, type attribute, className, variant styles |
| `src/test/components/GlassCard.test.tsx` | `src/components/glass/GlassCard.tsx` | 11 | Рендер, variant classes (glass/glass-subtle/glass-strong), padding (p-3/p-5/p-7), hoverable, custom className, complex children, ref forwarding |
| `src/test/components/GlassInput.test.tsx` | `src/components/glass/GlassInput.tsx` | 13 | Рендер, label, error message, icon, onChange, placeholder, password type, disabled, ref forwarding, error styling |
| `src/test/components/GlassToast.test.tsx` | `src/components/glass/GlassToast.tsx` | 6 | GlassToastContainer: empty state, success/error/warning/info toasts, description, click-to-dismiss, multiple toasts |

---

## Инфраструктура тестирования

### Конфигурация

| Файл | Назначение |
|------|-----------|
| `vitest.config.ts` | Vitest конфиг: jsdom environment, pool: forks + singleFork, coverage scoping, path aliases |
| `src/test/setup.ts` | Universal mocks: Tauri APIs, Stronghold, SQL, Howler, localStorage/sessionStorage, URL static methods |
| `src/test/setup.jsdom.ts` | jsdom-specific: jest-dom matchers, motion/react mock, react-router-dom navigation mocks, Web Audio API mock |

### Стратегия моков

| Зависимость | Стратегия |
|-------------|-----------|
| `@tauri-apps/api/core` (invoke) | `vi.mock()` → возвращает null по умолчанию |
| `@tauri-apps/plugin-stronghold` | `vi.mock()` → полная заглушка с insert/get/remove |
| `@tauri-apps/plugin-sql` | `vi.mock()` → execute/select заглушки |
| `motion/react` | `vi.mock()` → заменяет `motion.div/button/span` на чистые React-элементы |
| `react-router-dom` | Частичный mock: реальный модуль + overrides для useNavigate/useParams/useLocation |
| `localStorage/sessionStorage` | Кастомная реализация на `Map` с `_reset()` |
| `AudioContext` | Мок объект если `typeof AudioContext === 'undefined'` |
| Tauri detection | `'__TAURI_INTERNALS__' in window` → false в тестах → dev mode |

### Производительность

- `pool: 'forks'` + `singleFork: true` — последовательное выполнение (предотвращает OOM от параллельных jsdom-окружений)
- `NODE_OPTIONS="--max-old-space-size=6144"` — 6GB heap для jsdom
- Coverage scope ограничен протестированными модулями (избегает false fails по непокрытым pages/services)

---

## Найденные баги в production-коде

В процессе написания тестов обнаружены и исправлены **2 бага** в `src/lib/chunking.ts`:

### Bug 1: `findBreakPoint` — некорректная обработка `lastIndexOf() === -1`

**Проблема:** Когда `lastIndexOf` возвращает -1 (паттерн не найден), но `minPosition` отрицательный (например, -3750), проверка `-1 > -3750` давала `true`, и функция возвращала позицию 1 вместо перехода к следующему приоритету.

**Исправление:** Добавлены явные проверки `!== -1`:
```typescript
if (paragraphBreak !== -1 && paragraphBreak > minPosition) return paragraphBreak + 2;
if (lineBreak !== -1 && lineBreak > minPosition) return lineBreak + 1;
if (spaceBreak !== -1 && spaceBreak > minPosition) return spaceBreak + 1;
```

### Bug 2: `chunkTranscript` — бесконечный цикл в конце текста

**Проблема:** Когда `end >= text.length` после последнего чанка, но `position = end - overlapChars` всё ещё меньше `text.length`, цикл не завершался, вызывая `RangeError: Invalid array length`.

**Исправление:** Добавлен ранний выход после добавления финального чанка:
```typescript
chunks.push(text.slice(position, end).trim());
if (end >= text.length) break;  // ← добавлено
position = end - overlapChars;
```

---

## Нереализованные части (вне scope MVP-тестов)

| Область | Причина |
|---------|---------|
| Rust тесты (`cargo test`) | Требует Tauri Rust environment, отдельные unit тесты для `call_whisper_api`, `validate_openai_key` и пр. |
| Integration тесты (MSW) | Требует мокирование OpenAI Whisper + Claude/GPT-4o HTTP endpoints, полный pipeline flow |
| E2E тесты (Playwright) | Требует запущенное Tauri-окно или WebView2 эмуляцию |
| Whisper/Claude/OpenAI services | Сложная Tauri-интеграция; `invoke()` цепочки; требует отдельный MSW layer |
| Pages (7 страниц) | Зависят от stores + router + services; требуют complete integration setup |
| Edge cases | XSS в именах проектов, SQL injection, 500MB файлы, 50K+ символов артефактов |
