# Исследование рынка: Aether
Data: 2026-03-20

## Конкуренты

### Облачные/SaaS (meeting-first)

| Продукт | Платформа | Цена | Сильные стороны | Слабые стороны | Что можно взять |
|---------|-----------|------|----------------|-----------------|-----------------|
| **Otter.ai** | Web, macOS, Win, iOS, Android | Free 300 min/мес, Pro 16.99 USD/мес, Business 30 USD/мес | Реалтайм транскрипция встреч, Zoom/Teams/Meet, speaker ID, AI-саммари, поиск по архиву | Только 3 языка (EN/FR/ES), облако, подписка, точность ~85% | Формат AI-саммари встреч |
| **Fireflies.ai** | Web, Chrome ext, мобильные | Free 800 min/мес, Pro 10 USD/мес, Business 19 USD/мес | 100+ языков, точность 95+%, CRM-интеграции (Salesforce, HubSpot, Pipedrive), sentiment analysis, action items | Облачная обработка, подписка | Action items, sentiment analysis |
| **Fathom** | Web, macOS, Win | Free (базовый), Premium 19 USD/мес | Лучший бесплатный план, нативный клиент | Только встречи (не файлы) | Нативный клиент + AI-фичи |
| **TurboScribe** | Web | Free 3 файла/день, 10 USD/мес | 98 языков, 130+ перевода, batch | Только веб | Мультиязычный перевод |

### Desktop-first (file transcription)

| Продукт | Платформа | Цена | Сильные стороны | Слабые стороны | Что можно взять |
|---------|-----------|------|----------------|-----------------|-----------------|
| **MacWhisper** | macOS | EUR 59 (разовая) | Локальная обработка, приватность, batch, хороший UI | Только macOS, GUI для whisper.cpp, нет AI-постобработки | Чистый UI |
| **Whisper Transcription** | macOS, iOS | 4.99 USD (разовая) | Дешевле в 16 раз, LarMe-v3 Turbo, 100+ языков | Меньше экспорта, нет batch | Минимализм |
| **SuperWhisper** | macOS, iOS/iPad | 249 USD lifetime | Плагинная архитектура, множество AI-моделей | Высокая цена, баги | Плагинная архитектура |
| **VoiceInk** | macOS | 25-39 USD (разовая) | Полный офлайн, нулевой сбор данных, 100+ языков | Только macOS | Приватность как маркетинг |
| **Voibe** | macOS | 99 USD lifetime | Задержка <300мс, HIPAA-safe, Developer Mode | Только macOS | Developer Mode |
| **BetterDictation** | macOS (M1+) | 39 USD lifetime | Apple Neural Engine, офлайн | Только Apple Silicon | Оптимизация под чип |
### Dictation-first (real-time)

| Продукт | Платформа | Цена | Сильные стороны | Слабые стороны | Что можно взять |
|---------|-----------|------|----------------|-----------------|-----------------|
| **Wispr Flow** | macOS | Free 2000 слов/нед, 12-15 USD / мес | AI error correction, контекстное форматирование | Требует интернет | AI коррекция текста |
| **Aqua Voice** | macOS | 10 USD / мес | Реалтайм, менее 1 сек вставка, 5/5 точность | Подписка | Скорость вставки |

---

## Open source аналоги

| Проект | Stars | Фреймворк | Платформы | Что интересного |
|--------|-------|-----------|-----------|-----------------|
| **[Buzz](https://github.com/chidiwilliams/buzz)** | 13,800+ | Python + PyQt | macOS, Win, Linux | Лидер OSS. Whisper/cpp/Faster, 1000+ языков, diarization, реалтайм транскрипция, Presentation Window, видео |
| **[Vibe](https://github.com/thewh1teagle/vibe)** | 5,600+ | **Tauri** + TS + Rust | macOS, Win, Linux | ПРЯМОЙ КОНКУРЕНТ по стеку! GPU (Nvidia/AMD/Intel), batch, diarization, Claude API, Ollama, 7 форматов, CLI+API. 37 контрибьюторов, v3.0.19 (март 2026) |
| **[OpenTranscribe](https://github.com/davidamacey/OpenTranscribe)** | ~500 | Svelte + FastAPI  | Self-hosted | Diarization, поиск, коллаборация |
| **[transcribe-anything](https://github.com/zackez/transcribe-anything)** | 800+ | Python CLI | Cross-platform | Multi-backend, Mac ARM |

### КРИТИЧЕСКИ ВАЖНО: Vibe -- прямой конкурент

Vibe на том же стеке (Tauri + TS + Rust + whisper.cpp), 5.6k stars, 37 контрибьюторов.
GPU-ускорение, Claude API, CLI + HTTP API, активная разработка.
Aether должен четко отличаться от Vibe.

---

## UX лучшие практики

**1. Синхронизированный интерфейс "аудио + текст"**
- Waveform слева, транскрипт справа, синхронизированы
- Клик по waveform -> курсор на тексте
- Выделение текста -> подсветка сегмента на waveform

**2. Визуальное редактирование сегментов**
- Drag-and-drop на таймлайне
- Swim lanes для overlapping регионов

**3. Keyboard-first навигация**
- Play/Pause, Jump, Split, Merge, Delete без мыши
- Кастомизируемые хоткеи

**4. Прогресс транскрипции**
- Прогресс-бар + ETA
- Извлечь аудио перед отправкой (видео 4GB -> аудио 20-40MB)

**5. Множественный экспорт**
- TXT, SRT, VTT, DOCX, PDF, JSON, HTML

**6. Speaker Diarization**
- Цветовое кодирование спикеров
- Переименование Speaker 1 -> "Иван Петров"

**7. Batch Processing**
- Очередь файлов с прогрессом, drag-and-drop

**8. Персонализация**
- Инструмент адаптируется к стилю пользователя (а не наоборот)

---

## Размер бандла Таури-приложений

| Метрика | Tauri 2.x | Electron | Разница |
|---------|-----------|----------|---------|
| Минимальный бандл | <600 KB | ~150 MB | ~250x |
| Типичное приложение | 3-10 MB | 100-250 MB | ~25x |
| Бенчмарк (gethopp) | 8.6 MiB | 244 MiB | 28x |
| RAM (idle) | 30-50 MB | 200-300 MB | ~5x |
| Startup time | <500ms | 1-2 сек | 2-4x |

**Aether: 1.17 MB -- ОТЛИЧНО.** Верхний диапазон оптимизированных Tauri-приложений.

---

## Тренды дизайна: Dark Glassmorphism

**Вердикт:** Dark Glassmorphism -- доминирующий тренд 2025-2026.

- Темный фон (#1A1A1E) + полупрозрачные стеклянные панели
- Frosted glass (backdrop-filter: blur) на темном фоне
- Apple WWDC 2025 "Liquid Glass" по всей macOS/iOS
- Премиально, технологично, лучше контраст

**Для Aether:** темная тема + glass эффекты (GlassButton.tsx) -- точно в тренде.
Палитра dark+gold/amber (#C8A050, #E08040) -- уникальный стиль.

---

## Вывод

### Уникальные преимущества Aether:

1. **AI-артефакты из транскрипции** -- структурированные артефакты через 9 LLM с fallback (уникально)
2. **9 LLM-провайдеров с fallback* -- нет ни у кого из десктоп-конкурентов
3. **Бандл 1.17 MB** -- легчайший из всех
4. **Dark Glassmorphism + Gold/Amber** -- уникальный дизайн
5. **Приватность + интеллект** -- локальное хранение + мощные AI-артефакты

### Что СТОИТ ДОБАВИТЬ:

| Фича | Приоритет | Конкуренты | Сложность |
|------|-----------|-----------|-----------|
| Speaker Diarization | ВЫСОКИЙ | Buzz, Vibe, Otter, Fireflies | Средняя |
| Waveform + текст синхронизация | ВЫСОКИЙ | Buzz, HumanSignal | Средняя |
| Batch processing | СРЕДНИЙ | Vibe, MacWhisper | Низкая |
| Keyboard shortcuts | СРЕДНИЙ | Buzz, все pro | Низкая |
| Множество форматов | СРЕДНИЙ | Vibe (7 форматов) | Низкая |
| GPU процессинг | НИЗКИЙ | Vibe | Высокая |

### Что НЕ СТОИТ добавлять:

- CRM-интеграции -- ниша Fireflies/Otter
- Zoom/Teams-бот -- требует облака
- Подписочная модель -- раздражение пользователей
- Web-версия -- размывает desktop-first

### Позиционирование:

**"Приватный АI-ассистент для встреч"**
- Транскрибирует локально (как Buzz/Vibe)
- Генерирует умные артефакты через 9 LLM (уникально)
- Весит 1.17 MB (легчайшее)
- Премиальный продукт (Dark Glass + Gold)

**Главный конкурент: Vibe** -- тот же стек, 5.6k stars.
Дифференциация = AI-артефакты + мультипровайдерность + дизайн.

---

## Источники

- [Fireflies vs Otter 2026](https://thebusinessdive.com/fireflies-ai-vs-otter-ai)
- [Otter.ai Pricing 2026](https://www.outdoo.ai/blog/otter-ai-pricing)
- [MacWhisper Alternatives 2026](https://www.getvoibe.com/blog/macwhisper-alternatives/)
- [Awesome Whisper](https://github.com/sindresorhus/awesome-whisper)
- [Buzz](https://github.com/chidiwilliams/buzz)
- [Vibe](https://github.com/thewh1teagle/vibe)
- [Tauri App Size](https://v2.tauri.app/concept/size/)
- [Tauri vs Electron](https://www.gethopp.app/blog/tauri-vs-electron)
- [Dark Glassmorphism 2026](https://medium.com/@developer_89726/dark-glassmorphism-the-aesthetic-that-will-define-ui-in-2026-93aa4153088f)
- [Audio Transcription UI](https://humansignal.com/blog/building-a-better-ui-for-audio-transcription-at-scale/)
- [Vibe + Buzz Lab Notes](https://nlsblog.org/2025/12/17/lab-notes-transcription-with-vibe-and-buzz/)
- [Tauri v2 Optimization](https://www.oflight.co.jp/en/columns/tauri-v2-performance-bundle-size)
- [Otter vs Fireflies vs Fathom](https://www.itsconvo.com/blog/otter-vs-fireflies-vs-fathom)
