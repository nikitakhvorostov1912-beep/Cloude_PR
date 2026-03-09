# Отладочные паттерны и решения

## Аудио: "play() OK но нет звука"

### Быстрая диагностика (3 шага, < 1 минуты)

1. **Проверить громкость файлов** — ffmpeg volumedetect:
   ```bash
   for f in *.mp3; do
     vol=$(ffmpeg -i "$f" -af volumedetect -f null NUL 2>&1 | grep max_volume | sed 's/.*max_volume: //;s/ dB//')
     echo "$f: max=$vol dB"
   done
   ```
   - Нормально: -1 до -20 dB
   - **ТИШИНА: -91 dB** — файл содержит пустой аудиопоток, нужна регенерация

2. **Проверить AudioContext state** в браузере:
   ```javascript
   new AudioContext().state // "suspended" = ПРОБЛЕМА
   ```

3. **Проверить console.warn** — наши исправления логируют блокировку:
   ```
   [demo-audio] voice play() blocked: NotAllowedError /pitch/audio/op-1.mp3
   ```

### Корневые причины (ранг по частоте)

| # | Причина | Как определить | Решение |
|---|---------|----------------|---------|
| 1 | **Тихие MP3 (-91 dB)** — pedalboard PitchShift в чанковом режиме генерирует тишину | ffmpeg volumedetect → max_volume < -60 dB | Регенерация через ffmpeg: `ffmpeg -i src.mp3 -af "asetrate=44100*2^(N/12),aresample=44100" out.mp3` |
| 2 | **AudioContext suspended** — не await resume() | `audioContext.state === "suspended"` | `await audioContext.resume()` в unlockAudio(), вызывать из user gesture |
| 3 | **setTimeout разрывает user gesture** — Chrome даёт ~1с на gesture scope | play() reject → NotAllowedError | Убрать setTimeout между click и AudioContext/play() |
| 4 | **play().catch() глотает ошибки** | Нет ошибок в консоли, но нет звука | Добавить console.warn в catch |
| 5 | **Вкладка/сайт замьючен** | Звук работает на других сайтах | chrome://settings/content/sound |

### pedalboard PitchShift — баг

**НИКОГДА не использовать чанковую обработку с PitchShift:**
```python
# ПЛОХО — генерирует тишину:
while f.tell() < f.frames:
    chunk = f.read(int(f.samplerate))
    o.write(board(chunk, f.samplerate, reset=False))

# ХОРОШО — весь файл сразу:
audio_data = f.read(f.frames)
processed = board(audio_data, f.samplerate)
o.write(processed)
```

**Лучше всего — ffmpeg для pitch shift:**
```bash
# Pitch shift на N полутонов (без изменения скорости):
ffmpeg -i input.mp3 -af "asetrate=44100*2^(N/12),aresample=44100" -b:a 192k output.mp3

# Примеры:
# +0.5 полутона: 2^(0.5/12)
# -1.0 полутон:  2^(-1/12)
# +скорость 10%: добавить ,atempo=1.10
```

### Chrome Autoplay — правильный паттерн

```typescript
// 1. Экспортировать unlockAudio() из аудио-модуля
export async function unlockAudio(): Promise<void> {
  if (!audioContext || audioContext.state === "closed") {
    audioContext = new AudioContext();
  }
  if (audioContext.state === "suspended") {
    await audioContext.resume();
  }
}

// 2. Вызывать НАПРЯМУЮ из click handler (без setTimeout!)
const startDemo = useCallback(async () => {
  await unlockAudio();  // ← прямо из клика
  resetDemo();
  await runDemo();      // ← await для обработки ошибок
}, [runDemo, resetDemo]);
```

### После генерации аудио — обязательная проверка

Всегда проверять что файлы не тихие:
```bash
# Если max_volume < -60 dB — файл содержит тишину
ffmpeg -i file.mp3 -af volumedetect -f null NUL 2>&1 | grep max_volume
```

## Preview Tool: аудио не слышно — это нормально

Headless Chrome (Playwright/Preview) **не имеет аудиовыхода**. `play() OK` при этом — нормальное поведение. Для проверки:
- Смотреть `audio.paused === false` и `audio.currentTime > 0`
- Проверять console на ошибки/warnings
- Реальный звук проверять только в настоящем браузере
