/**
 * Сервис транскрипции через OpenAI Whisper API.
 * Обрабатывает edge cases: EC-05 (качество), EC-06 (нет речи), EC-08 (retry).
 */

const WHISPER_API_URL = 'https://api.openai.com/v1/audio/transcriptions';

/** Максимальный размер файла для Whisper API: 25 MB */
const MAX_FILE_SIZE_MB = 25;

/** Retry конфигурация (EC-08) */
const MAX_RETRIES = 3;
const RETRY_DELAYS = [30_000, 60_000, 120_000]; // 30с, 60с, 120с

export interface WhisperResult {
  text: string;
  segments: WhisperSegment[];
  language: string;
  duration: number;
  qualityWarnings: string[];
}

export interface WhisperSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  speaker?: string;
  avgLogprob?: number;
  noSpeechProb?: number;
}

export interface TranscriptionProgress {
  stage: 'preparing' | 'uploading' | 'transcribing' | 'processing';
  progress: number; // 0-100
  message: string;
}

/**
 * Транскрибирует аудиофайл через Whisper API.
 */
export async function transcribeAudio(
  audioFile: File | Blob,
  apiKey: string,
  onProgress?: (p: TranscriptionProgress) => void,
): Promise<WhisperResult> {
  // Валидация размера файла
  const sizeMb = audioFile.size / (1024 * 1024);
  if (sizeMb > MAX_FILE_SIZE_MB) {
    throw new WhisperError(
      `Файл слишком большой: ${sizeMb.toFixed(1)} МБ. Максимум: ${MAX_FILE_SIZE_MB} МБ.`,
      'FILE_TOO_LARGE',
    );
  }

  onProgress?.({ stage: 'preparing', progress: 10, message: 'Подготовка аудио...' });

  // Формируем запрос
  const formData = new FormData();
  formData.append('file', audioFile, audioFile instanceof File ? audioFile.name : 'audio.wav');
  formData.append('model', 'whisper-1');
  formData.append('response_format', 'verbose_json');
  formData.append('language', 'ru');
  formData.append('timestamp_granularities[]', 'segment');

  onProgress?.({ stage: 'uploading', progress: 30, message: 'Отправка на сервер...' });

  // Retry с exponential backoff (EC-08)
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      if (attempt > 0) {
        const delay = RETRY_DELAYS[attempt - 1];
        onProgress?.({
          stage: 'uploading',
          progress: 30,
          message: `Повторная попытка через ${delay / 1000} сек... (${attempt}/${MAX_RETRIES})`,
        });
        await sleep(delay);
      }

      onProgress?.({ stage: 'transcribing', progress: 50, message: 'Транскрипция...' });

      const response = await fetch(WHISPER_API_URL, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorBody = await response.text().catch(() => '');
        const statusCode = response.status;

        // Определяем тип ошибки
        if (statusCode === 401) {
          throw new WhisperError('Невалидный API-ключ OpenAI.', 'INVALID_KEY');
        }
        if (statusCode === 429) {
          lastError = new WhisperError('Превышен лимит запросов. Повторная попытка...', 'RATE_LIMIT');
          continue; // retry
        }
        if (statusCode >= 500) {
          lastError = new WhisperError(`Ошибка сервера OpenAI (${statusCode}).`, 'SERVER_ERROR');
          continue; // retry
        }

        throw new WhisperError(
          `Ошибка Whisper API: ${statusCode} — ${errorBody.slice(0, 200)}`,
          'API_ERROR',
        );
      }

      onProgress?.({ stage: 'processing', progress: 80, message: 'Обработка результатов...' });

      const data = await response.json();
      const result = processWhisperResponse(data);

      onProgress?.({ stage: 'processing', progress: 100, message: 'Транскрипция завершена' });

      return result;
    } catch (error) {
      if (error instanceof WhisperError && (error.code === 'INVALID_KEY' || error.code === 'API_ERROR' || error.code === 'FILE_TOO_LARGE')) {
        throw error; // Не повторяем для этих ошибок
      }
      lastError = error instanceof Error ? error : new Error(String(error));
    }
  }

  throw new WhisperError(
    `Транскрипция не удалась после ${MAX_RETRIES} попыток: ${lastError?.message || 'неизвестная ошибка'}`,
    'MAX_RETRIES_EXCEEDED',
  );
}

/**
 * Обрабатывает ответ Whisper API.
 * Проверяет качество (EC-05) и наличие речи (EC-06).
 */
function processWhisperResponse(data: Record<string, unknown>): WhisperResult {
  const text = (data.text as string) || '';
  const language = (data.language as string) || 'ru';
  const duration = (data.duration as number) || 0;
  const rawSegments = (data.segments as Array<Record<string, unknown>>) || [];

  const segments: WhisperSegment[] = rawSegments.map((seg, i) => ({
    id: (seg.id as number) ?? i,
    start: (seg.start as number) || 0,
    end: (seg.end as number) || 0,
    text: ((seg.text as string) || '').trim(),
    avgLogprob: seg.avg_logprob as number | undefined,
    noSpeechProb: seg.no_speech_prob as number | undefined,
  }));

  const qualityWarnings: string[] = [];

  // EC-06: Проверка на отсутствие речи
  if (!text.trim() || segments.length === 0) {
    throw new WhisperError(
      'В записи не обнаружена речь. Возможно, выбран неверный файл.',
      'NO_SPEECH',
    );
  }

  // EC-05: Оценка качества транскрипции
  const avgNoSpeechProb = segments.reduce((sum, s) => sum + (s.noSpeechProb || 0), 0) / segments.length;
  const avgLogProb = segments.reduce((sum, s) => sum + (s.avgLogprob || 0), 0) / segments.length;

  if (avgNoSpeechProb > 0.5) {
    qualityWarnings.push('Высокий уровень шума');
  }

  if (avgLogProb < -1.0) {
    qualityWarnings.push('Низкая уверенность распознавания');
  }

  // Проверяем процент сегментов с низким качеством
  const lowQualitySegments = segments.filter((s) => (s.noSpeechProb || 0) > 0.7).length;
  const lowQualityPercent = (lowQualitySegments / segments.length) * 100;

  if (lowQualityPercent > 30) {
    qualityWarnings.push(`${lowQualityPercent.toFixed(0)}% записи содержат шум или тишину`);
  }

  return {
    text,
    segments,
    language,
    duration,
    qualityWarnings,
  };
}

/**
 * Форматирует таймкод из секунд в MM:SS.
 */
export function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Конвертирует сегменты Whisper в формат стенограммы.
 */
export function segmentsToTranscript(segments: WhisperSegment[]): string {
  return segments
    .map((seg) => `[${formatTimestamp(seg.start)}] ${seg.text}`)
    .join('\n');
}

/**
 * Проверяет валидность API-ключа OpenAI (тестовый запрос).
 */
export async function validateOpenAIKey(apiKey: string): Promise<{ valid: boolean; error?: string }> {
  try {
    const response = await fetch('https://api.openai.com/v1/models', {
      headers: { Authorization: `Bearer ${apiKey}` },
    });

    if (response.ok) return { valid: true };
    if (response.status === 401) return { valid: false, error: 'Невалидный API-ключ' };
    return { valid: false, error: `Ошибка проверки: ${response.status}` };
  } catch {
    return { valid: false, error: 'Нет подключения к API' };
  }
}

/** Кастомная ошибка Whisper */
export class WhisperError extends Error {
  constructor(
    message: string,
    public code: 'FILE_TOO_LARGE' | 'INVALID_KEY' | 'RATE_LIMIT' | 'SERVER_ERROR' | 'API_ERROR' | 'NO_SPEECH' | 'MAX_RETRIES_EXCEEDED',
  ) {
    super(message);
    this.name = 'WhisperError';
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
