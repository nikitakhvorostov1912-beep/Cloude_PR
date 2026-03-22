# Технический аудит: Aether
Дата: 2026-03-20

---

## Критические проблемы (P0 — сломано)

### P0-1: Неполная проверка STT-ключей в PipelinePage.tsx
**Файл:** `src/pages/PipelinePage.tsx`, строки 159–165

```typescript
const sttKeyMap: Record<string, keyof typeof apiKeys> = { groq: 'groqKey' };
const sttKeyField = sttKeyMap[sttProvider] || 'groqKey';
```

Карта содержит только `groq`. Если пользователь выбрал `openai` или `gemini` как STT-провайдер, `sttKeyMap[sttProvider]` вернёт `undefined`, и fallback будет `groqKey`. Проверка пройдёт даже если ключа OpenAI/Gemini нет, но пайплайн сломается позже. Для `claude` и остальных LLM-провайдеров аналогичная карта `llmKeyMap` тоже не содержит `claude` и `openai` (строка 168–171) — при `routingMode === 'single'` с провайдером `claude` или `openai` проверка всегда будет падать в fallback `'groqKey'`.

**Исправление:** заменить на полные карты, аналогичные `LLM_KEY_MAP` / `STT_KEY_MAP` из `pipeline.service.ts`.

### P0-2: Схемы Zod в schemas.ts не покрывают все провайдеры
**Файл:** `src/lib/schemas.ts`, строки 43–44

```typescript
const LLMProviderSchema = z.enum(['openai', 'claude', 'gemini', 'groq', 'deepseek', 'mimo']);
const STTProviderSchema = z.enum(['openai', 'groq']);
```

Отсутствуют провайдеры: `cerebras`, `mistral`, `openrouter` (LLM) и `gemini` (STT). Если пользователь выберет любой из них в настройках, `validatePipelineConfig()` вернёт `{ success: false }` и пайплайн не запустится — несмотря на то что провайдеры полностью реализованы в `llm.service.ts`. Это тихое блокирование без понятного сообщения пользователю.

**Исправление:** синхронизировать схемы с типами из `src/types/api.types.ts`.

### P0-3: CSP не содержит домены для 6 из 9 LLM-провайдеров
**Файл:** `src-tauri/tauri.conf.json`, строка 27

```
connect-src 'self' https://api.openai.com https://api.anthropic.com
```

Отсутствуют: `api.groq.com`, `generativelanguage.googleapis.com`, `api.deepseek.com`, `api.xiaomimimo.com`, `api.cerebras.ai`, `api.mistral.ai`, `openrouter.ai`. В production Tauri-сборке (не dev с proxy) запросы к этим доменам будут блокироваться CSP. Dev-режим работает через Vite proxy и CSP не применяется — баг не виден в разработке.

**Исправление:** добавить все домены провайдеров в `connect-src`. Также отсутствует `blob:` в `connect-src` — нужен для audio blob.

---

## Серьёзные проблемы (P1 — мешает работе)

### P1-1: ArtifactTabs.tsx — мёртвый компонент
**Файл:** `src/components/artifacts/ArtifactTabs.tsx`

Компонент нигде не импортируется и не используется. ViewerPage реализует свои табы inline. Компонент занимает место в бандле (незначительно), но создаёт путаницу при навигации по коду.

### P1-2: Нет proxy для cerebras, mistral, openrouter в Vite
**Файл:** `vite.config.ts`

Proxy настроен только для: anthropic, openai, groq, gemini, deepseek, mimo. Для `cerebras`, `mistral`, `openrouter` proxy отсутствует. В dev-режиме эти провайдеры будут получать CORS-ошибки при прямом fetch. Tauri production работает через Rust backend — проблемы нет, но разработка без Tauri окна сломана.

### P1-3: GenerateArtifactPanel не использует контекст транскрипции
**Файл:** `src/components/artifacts/GenerateArtifactPanel.tsx`

При генерации нового артефакта из ViewerPage компонент вызывает `generateArtifact()` напрямую, не передавая транскрипцию встречи в промпт. Артефакт генерируется "вслепую" без исходных данных.

### P1-4: file-storage.service.ts — storeAudioFile нигде не вызывается
**Файл:** `src/services/file-storage.service.ts`

Функция `storeAudioFile` определена, но в `PipelinePage.tsx` не вызывается при создании встречи. При автозапуске пайплайна (из ProjectPage → pipeline) `getAudioFile()` будет возвращать `null`. Сценарий "возобновить обработку" работает только через blob URL (живёт в рамках одной вкладки).

### P1-5: StreamingText накапливается без лимита
**Файл:** `src/stores/pipeline.store.ts`, строка 102

```typescript
appendStreamingText: (text) => set((s) => ({ streamingText: s.streamingText + text })),
```

Строка неограниченно растёт. При длинных записях с чанкингом может накапливаться несколько десятков KB в Zustand-персисте (localStorage).

### P1-6: Двойная валидация файлов в pipeline.service.ts
**Файл:** `src/services/pipeline.service.ts`, строки 209–227

Файлы сначала валидируются в цикле (строка 209), потом снова фильтруются через повторный вызов `validateAudioFile(f.file)` (строка 225). Дублирование.

---

## Улучшения (P2 — стоит сделать)

### P2-1: Нет lazy loading для роутов
**Файл:** `src/App.tsx`
Все 9 страниц импортируются синхронно. Рекомендуется `React.lazy()` + `Suspense` хотя бы для ViewerPage, PipelinePage, SettingsPage.

### P2-2: PipelinePage.tsx — 699 строк, функция handleStartPipeline 225 строк
**Файл:** `src/pages/PipelinePage.tsx`
Разделить на: `useApiKeyValidation()`, `usePipelineRunner()`, `useCumulativeContext()`.

### P2-3: export.service.ts — 795 строк
**Файл:** `src/services/export.service.ts`
Разбить на `src/services/export/generators/` (по файлу на тип) + `export.service.ts` как orchestrator.

### P2-4: pickBestProvider() не используется извне
**Файл:** `src/lib/provider-router.ts`, строка 88
Экспортируется но не импортируется ни в одном файле.

### P2-5: Нет обработки ошибок Stronghold при старте
**Файл:** `src/App.tsx`, строки 58–61
Ошибка логируется в console.error, пользователь не видит UI-уведомления.

### P2-6: Rate limiter использует localStorage, не Stronghold
**Файл:** `src/lib/rate-limiter.ts`, строки 46, 60
Несоответствие подходу — ключи в Stronghold, статистика в localStorage. Приемлемо, но стоит задокументировать.

### P2-7: Бесполезный @tauri-apps/plugin-sql в dependencies
**Файл:** `package.json`
Установлен, но в коде нет ни одного импорта. Лишняя зависимость (~50 KB в Rust bundle).

### P2-8: Нет React.memo для чистых компонентов views
**Файлы:** `src/components/artifacts/views/ProtocolView.tsx`, `RequirementsView.tsx` и др.
View-компоненты принимают только `data` prop, нет side effects. Без `React.memo` перерендерятся при любом изменении родительского состояния.

### P2-9: WaveformPlayer.tsx — проверить использование
**Файл:** `src/components/audio/WaveformPlayer.tsx`
Используется только в ProjectPage.tsx, нужно проверить рендерится ли реально.

---

## Хорошее (что работает правильно)

1. **Безопасность ключей** — Tauri Stronghold реализован корректно в `keys.service.ts`. Ключи не попадают в localStorage (`partialize` в settings.store явно их исключает). Dev-fallback использует sessionStorage.

2. **Immutable state** — все Zustand-операции создают новые объекты через spread operator. Мутаций нет.

3. **Retry + Fallback архитектура** — `llm.service.ts` и `whisper.service.ts` реализуют правильный паттерн: retry с backoff, автоматическое переключение провайдеров при rate limit. Partial success: даже если часть артефактов не сгенерировалась — результат сохраняется.

4. **JSON auto-repair** — `validators.ts` реализует 3-попытки парсинга с очисткой markdown, trailing commas, незакрытыми скобками.

5. **Chunking для длинных транскриптов** — `lib/chunking.ts` разбивает транскрипты на части, `pipeline.service.ts` объединяет через Map-Reduce.

6. **AbortController** — пайплайн поддерживает отмену (`options?.signal?.aborted` проверяется в 3 точках). Прерванные встречи помечаются как `error`.

7. **Auto-routing с fan-out** — распределение артефактов по нескольким провайдерам параллельно (до 4x ускорение) через `provider-router.ts`.

8. **Кумулятивный контекст** — при повторных встречах предыдущие артефакты передаются в промпт для накопления.

9. **Pipeline crash recovery** — при перезапуске App.tsx проверяет прерванный пайплайн и помечает встречу как `error`.

10. **validateArtifactSchema** правильно разделяет `valid` и `isEmpty`.

---

## Мёртвый код

| Файл | Причина |
|------|---------|
| `src/components/artifacts/ArtifactTabs.tsx` | Нигде не импортируется |
| `src/lib/provider-router.ts` — `pickBestProvider()` | Экспортируется но не импортируется |
| `@tauri-apps/plugin-sql` в `package.json` | Не используется в коде |
| `src/services/file-storage.service.ts` — `storeAudioFile()` | Определена, но не вызывается |

---

## Производительность

### Бандл: 1.17 MB — анализ

- `vendor-docx` chunk: `docx` (~400 KB) + `jszip` (~40 KB) + `file-saver` (~2 KB) ≈ **440 KB** — загружается при старте, хотя нужен только при экспорте
- `vendor-motion` chunk: `motion` (~120 KB) ≈ **120 KB**
- Основной JS: ~587 KB = приложение + оставшиеся deps

**Что раздувает бандл:**
- `docx@9.6.1` (~400 KB minified) — самая тяжёлая. Решение: динамический импорт при первом использовании
- `motion@12.36.0` (~120 KB) — используется на каждой странице, lazy loading нецелесообразен
- `howler@2.2.4` (~30 KB) — небольшой

**Мемоизация:**
- ViewerPage: `useMemo` есть, корректно
- PipelinePage: `useCallback` dep array на строке 376 очень длинный (14 зависимостей), возможны лишние перерендеры
- View-компоненты: `React.memo` отсутствует

---

## Архитектура

### Зависимости (layer diagram)
```
UI (Pages/Components)
  ↓
Stores (Zustand) ←→ Services
  ↓                    ↓
Types              lib/ (utilities)
                        ↓
                   External APIs (via Tauri / fetch)
```

### Смешение бизнес-логики с UI
**PipelinePage.tsx** содержит: создание проекта, построение кумулятивного контекста, проверку API-ключей, добавление встречи в store. 225-строчная функция `handleStartPipeline` — типичный "fat page".

### God service: pipeline.service.ts
693 строки, функция `runPipeline()` — 422 строки в одной функции.

### Дублирование маппингов провайдеров
`LLM_KEY_MAP` дублируется в: `pipeline.service.ts`, `provider-router.ts`, `PipelinePage.tsx` (неполный), `settings.store.ts`. Нет единого источника правды. Решение: вынести в `lib/constants.ts`.

### Циклических зависимостей нет
Цепочка чистая: pages → stores + services + components → lib → types.

---

## Безопасность

### Хорошо
- API-ключи в Tauri Stronghold (зашифрованный vault)
- Ключи исключены из Zustand localStorage persist
- Нет hardcoded secrets
- Input validation через Zod

### Проблемы
- **CSP неполная** (P0-3)
- **Пароль Stronghold детерминированный** (`keys.service.ts:14–24`): SHA-256 от пути к данным. Предсказуемо. Рекомендуется случайная соль при первом запуске.
- **Gemini STT: API-ключ в URL** (`whisper.service.ts:301`): виден в DevTools Network в dev-режиме.

---

## Тёмная тема

### Текущий статус: ТОЛЬКО СВЕТЛАЯ ТЕМА

- Фон: `#F0F4FF → #E8EEFF` (светло-голубой)
- Поверхности: `rgba(255,255,255,0.6-0.9)`
- Нет `@media (prefers-color-scheme: dark)`
- Нет CSS класса `.dark`
- Нет Tailwind `dark:` утилит

### Объём работы для редизайна в Dark Gold/Amber: ~7-8 часов

1. `globals.css`: замена токенов (~2ч)
2. `GlassButton/GlassCard/GlassInput/GlassPanel`: исправление hardcoded Tailwind (~3ч)
3. `BackgroundBlobs`: замена цветов (~1ч)
4. Тестирование контраста (~1ч)

**Ключевой файл:** `src/styles/globals.css` — замена CSS переменных даст ~70% эффекта.

---

## Пользовательские сценарии

### Сценарий 1: Upload → Transcribe → Artifacts
**Статус: PARTIAL**
- Цепочка DragDropZone → pipeline.service → llm.service → artifacts.store работает
- **BROKEN:** схемы Zod не включают все провайдеры (P0-2)
- **BROKEN:** CSP блокирует 6 из 9 провайдеров в production (P0-3)
- Файл НЕ сохраняется в IndexedDB (P1-4) — повторный запуск только в текущей сессии
- Обработка ошибок на каждом шаге — есть

### Сценарий 2: View → Export DOCX
**Статус: OK**
- Все 8 типов артефактов экспортируются
- ZIP-архив работает
- Edge case: при удалённом проекте/встрече нет обратной связи пользователю

### Сценарий 3: API Keys → Save
**Статус: OK**
- Stronghold шифрование, ключи переживают перезапуск
- Partial failure обрабатывается через Promise.allSettled
- UX проблема: нет индикатора загрузки при async загрузке ключей

---

## Важные файлы

| Файл | Роль |
|------|------|
| `src/services/pipeline.service.ts` | Центральный оркестратор пайплайна |
| `src/services/llm.service.ts` | Абстракция над 9 LLM-провайдерами |
| `src/services/whisper.service.ts` | STT с fallback chain |
| `src/services/keys.service.ts` | Stronghold интеграция |
| `src/lib/provider-router.ts` | Auto-routing / fan-out |
| `src/lib/validators.ts` | JSON auto-repair |
| `src/lib/schemas.ts` | Zod-валидация (СОДЕРЖИТ БАГИ P0-2) |
| `src/styles/globals.css` | Дизайн-система, токены цветов |
| `src/pages/PipelinePage.tsx` | Основной UI пайплайна (fat page) |
| `src/services/export.service.ts` | Генерация DOCX |
| `src-tauri/tauri.conf.json` | CSP (СОДЕРЖИТ БАГИ P0-3) |
