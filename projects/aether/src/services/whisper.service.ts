/**
 * Сервис транскрипции через Whisper API.
 * Поддерживает OpenAI Whisper и Groq Whisper (бесплатно).
 * В Tauri: вызов через Rust backend (API-ключ не виден в DevTools).
 * В dev: прямой fetch (только для разработки).
 */

import { invoke } from '@tauri-apps/api/core';
import type { STTProvider } from '@/types/api.types';
import {
  DEFAULT_STT_MODELS,
  PROVIDER_BASE_URLS,
  STT_DEV_ENDPOINTS,
  PROVIDER_NAMES,
} from '@/lib/constants';

/** Максимальный размер для одного запроса Whisper API: 25 MB */
const MAX_CHUNK_SIZE_MB = 25;

/** Размер чанка при разбиении: 20 MB (с запасом до лимита 25) */
const SPLIT_CHUNK_SIZE_MB = 20;

/** Retry конфигурация (EC-08) */
const MAX_RETRIES = 2;
const RETRY_DELAYS = [5_000, 15_000];

/** Таймаут: 5 минут */
const REQUEST_TIMEOUT_MS = 5 * 60 * 1000;

const isTauri = (): boolean => '__TAURI_INTERNALS__' in window;

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
  progress: number;
  message: string;
}

/** Список STT-провайдеров для fallback (в порядке приоритета: бесплатные первыми) */
const STT_FALLBACK_ORDER: STTProvider[] = ['groq', 'gemini', 'openai'];

/** Маппинг STT-провайдер → поле APIKeys */
const STT_KEY_MAP: Record<STTProvider, string> = {
  groq: 'groqKey',
  gemini: 'geminiKey',
  openai: 'openaiKey',
};

/**
 * Транскрибирует аудиофайл через Whisper API.
 * При rate limit автоматически переключается на другой STT-провайдер.
 *
 * @param sttProvider — предпочтительный провайдер ('openai' или 'groq')
 * @param fallbackApiKeys — все API-ключи для автопереключения при rate limit
 */
export async function transcribeAudio(
  audioFile: File | Blob,
  apiKey: string,
  sttProvider: STTProvider = 'groq',
  onProgress?: (p: TranscriptionProgress) => void,
  fallbackApiKeys?: Record<string, string>,
): Promise<WhisperResult> {
  const sizeMb = audioFile.size / (1024 * 1024);

  // Если файл > 25 МБ — автосплит через Tauri/ffmpeg
  if (sizeMb > MAX_CHUNK_SIZE_MB) {
    if (!isTauri()) {
      throw new WhisperError(
        `Файл ${sizeMb.toFixed(1)} МБ превышает лимит ${MAX_CHUNK_SIZE_MB} МБ. Запустите через «npm run tauri dev» для автоматического разбиения.`,
        'FILE_TOO_LARGE',
      );
    }
    return transcribeWithChunking(audioFile, apiKey, sttProvider, onProgress, fallbackApiKeys);
  }

  onProgress?.({ stage: 'preparing', progress: 10, message: 'Подготовка аудио...' });
  return transcribeSingleFile(audioFile, apiKey, sttProvider, onProgress, fallbackApiKeys);
}

/**
 * Транскрибирует большой файл целиком в Rust: split + API вызовы.
 * Данные не копируются обратно в JS между чанками — всё в одном invoke.
 * Fallback: если Gemini — чанкуем в JS (Gemini не Whisper-совместимый).
 */
async function transcribeWithChunking(
  audioFile: File | Blob,
  apiKey: string,
  sttProvider: STTProvider,
  onProgress?: (p: TranscriptionProgress) => void,
  fallbackApiKeys?: Record<string, string>,
): Promise<WhisperResult> {
  const { invoke } = await import('@tauri-apps/api/core');
  const sizeMb = audioFile.size / (1024 * 1024);

  // Gemini не поддерживает Whisper multipart — fallback на JS-чанкинг
  if (sttProvider === 'gemini') {
    return transcribeWithChunkingJS(audioFile, apiKey, sttProvider, onProgress, fallbackApiKeys);
  }

  onProgress?.({ stage: 'preparing', progress: 5, message: `Разбиение ${sizeMb.toFixed(1)} МБ и транскрипция в Rust...` });

  const arrayBuffer = await audioFile.arrayBuffer();
  const audioBytes = new Uint8Array(arrayBuffer);

  const model = DEFAULT_STT_MODELS[sttProvider];
  const endpointUrl = `${PROVIDER_BASE_URLS[sttProvider]}/audio/transcriptions`;

  console.log(`[Whisper] transcribe_chunked: ${sizeMb.toFixed(1)} МБ → ${endpointUrl} (${model})`);

  onProgress?.({ stage: 'transcribing', progress: 20, message: `Транскрипция ${sizeMb.toFixed(1)} МБ через Rust...` });

  let chunkJsons: string[];
  try {
    chunkJsons = await invoke('transcribe_chunked', {
      audioBytes,
      endpointUrl,
      apiKey,
      model,
      maxChunkMb: SPLIT_CHUNK_SIZE_MB,
    });
  } catch (err) {
    const msg = String(err);
    // Обработка ошибок API из Rust
    if (msg.includes('WHISPER_API_ERROR:')) {
      const statusMatch = msg.match(/WHISPER_API_ERROR:(\d+):/);
      const statusCode = statusMatch ? parseInt(statusMatch[1], 10) : 0;
      const providerName = PROVIDER_NAMES[sttProvider] || sttProvider;
      if (statusCode === 401) throw new WhisperError(`Невалидный API-ключ ${providerName}.`, 'INVALID_KEY');
      if (statusCode === 429) throw new WhisperError('Превышен лимит запросов.', 'RATE_LIMIT');
      if (statusCode >= 500) throw new WhisperError(`Ошибка сервера ${providerName} (${statusCode}).`, 'SERVER_ERROR');
      throw new WhisperError(`Ошибка Whisper API: ${statusCode}`, 'API_ERROR');
    }
    throw new WhisperError(`Ошибка транскрипции: ${msg}`, 'API_ERROR');
  }

  console.log(`[Whisper] Rust вернул ${chunkJsons.length} чанков`);

  // Собираем результаты из JSON-ответов
  const allSegments: WhisperSegment[] = [];
  const allTexts: string[] = [];
  const allWarnings: string[] = [];
  let totalDuration = 0;
  let detectedLanguage = 'ru';

  for (let i = 0; i < chunkJsons.length; i++) {
    const data = JSON.parse(chunkJsons[i]) as Record<string, unknown>;
    const chunkResult = processWhisperResponse(data);

    const offsetSegments = chunkResult.segments.map((seg) => ({
      ...seg,
      id: allSegments.length + seg.id,
      start: seg.start + totalDuration,
      end: seg.end + totalDuration,
    }));

    allSegments.push(...offsetSegments);
    allTexts.push(chunkResult.text);
    allWarnings.push(...chunkResult.qualityWarnings);
    totalDuration += chunkResult.duration;
    detectedLanguage = chunkResult.language;

    onProgress?.({
      stage: 'transcribing',
      progress: Math.round(((i + 1) / chunkJsons.length) * 90) + 5,
      message: `Обработка чанка ${i + 1}/${chunkJsons.length}...`,
    });
  }

  onProgress?.({ stage: 'processing', progress: 100, message: `Транскрипция завершена (${chunkJsons.length} чанков)` });

  return {
    text: allTexts.join('\n'),
    segments: allSegments,
    language: detectedLanguage,
    duration: totalDuration,
    qualityWarnings: [...new Set(allWarnings)],
  };
}

/**
 * JS-fallback чанкинг для провайдеров без Whisper-совместимого API (Gemini).
 * Использует split_audio_chunks из Rust, но API-вызовы делает из JS.
 */
async function transcribeWithChunkingJS(
  audioFile: File | Blob,
  apiKey: string,
  sttProvider: STTProvider,
  onProgress?: (p: TranscriptionProgress) => void,
  fallbackApiKeys?: Record<string, string>,
): Promise<WhisperResult> {
  const { invoke } = await import('@tauri-apps/api/core');
  const sizeMb = audioFile.size / (1024 * 1024);

  onProgress?.({ stage: 'preparing', progress: 5, message: `Разбиение ${sizeMb.toFixed(1)} МБ на чанки...` });

  const arrayBuffer = await audioFile.arrayBuffer();
  const audioBytes = new Uint8Array(arrayBuffer);

  const rawChunks = await invoke<Array<number[] | Uint8Array>>('split_audio_chunks', {
    audioBytes,
    maxChunkMb: SPLIT_CHUNK_SIZE_MB,
  });
  // Tauri 2 возвращает Vec<Vec<u8>> как Array<number[]> — конвертируем в Uint8Array
  const chunks = rawChunks.map((c) => (c instanceof Uint8Array ? c : new Uint8Array(c)));

  console.log(`[Whisper] Файл ${sizeMb.toFixed(1)} МБ разбит на ${chunks.length} чанков (JS-fallback)`);

  const allSegments: WhisperSegment[] = [];
  const allTexts: string[] = [];
  const allWarnings: string[] = [];
  let totalDuration = 0;
  let detectedLanguage = 'ru';

  for (let i = 0; i < chunks.length; i++) {
    const chunkBlob = new Blob([chunks[i]], { type: 'audio/mpeg' });
    const chunkSizeMb = chunkBlob.size / (1024 * 1024);

    onProgress?.({
      stage: 'transcribing',
      progress: Math.round((i / chunks.length) * 90) + 5,
      message: `Чанк ${i + 1}/${chunks.length} (${chunkSizeMb.toFixed(1)} МБ)...`,
    });

    const chunkResult = await transcribeSingleFile(
      chunkBlob, apiKey, sttProvider, undefined, fallbackApiKeys,
    );

    const offsetSegments = chunkResult.segments.map((seg) => ({
      ...seg,
      id: allSegments.length + seg.id,
      start: seg.start + totalDuration,
      end: seg.end + totalDuration,
    }));

    allSegments.push(...offsetSegments);
    allTexts.push(chunkResult.text);
    allWarnings.push(...chunkResult.qualityWarnings);
    totalDuration += chunkResult.duration;
    detectedLanguage = chunkResult.language;
  }

  onProgress?.({ stage: 'processing', progress: 100, message: `Транскрипция завершена (${chunks.length} чанков)` });

  return {
    text: allTexts.join('\n'),
    segments: allSegments,
    language: detectedLanguage,
    duration: totalDuration,
    qualityWarnings: [...new Set(allWarnings)],
  };
}

/**
 * Транскрибирует один файл (≤25 МБ) через цепочку провайдеров с retry.
 */
async function transcribeSingleFile(
  audioFile: File | Blob,
  apiKey: string,
  sttProvider: STTProvider,
  onProgress?: (p: TranscriptionProgress) => void,
  fallbackApiKeys?: Record<string, string>,
): Promise<WhisperResult> {
  // Построить цепочку: preferred первым, затем остальные с ключами
  const providerChain: Array<{ provider: STTProvider; key: string }> = [];
  providerChain.push({ provider: sttProvider, key: apiKey });

  if (fallbackApiKeys) {
    for (const fb of STT_FALLBACK_ORDER) {
      if (fb === sttProvider) continue;
      const fbKey = fallbackApiKeys[STT_KEY_MAP[fb]];
      if (fbKey) providerChain.push({ provider: fb, key: fbKey });
    }
  }

  let lastError: Error | null = null;
  const triedProviders = new Set<string>();

  for (const slot of providerChain) {
    const providerName = PROVIDER_NAMES[slot.provider] || slot.provider;

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      try {
        if (attempt > 0) {
          const delay = RETRY_DELAYS[attempt - 1];
          onProgress?.({
            stage: 'uploading',
            progress: 30,
            message: `Повтор ${providerName} через ${delay / 1000} сек... (${attempt}/${MAX_RETRIES})`,
          });
          await sleep(delay);
        }

        onProgress?.({ stage: 'transcribing', progress: 50, message: `Транскрипция через ${providerName}...` });

        let data: Record<string, unknown>;
        if (slot.provider === 'gemini') {
          data = await transcribeViaGemini(audioFile, slot.key, onProgress);
        } else {
          const model = DEFAULT_STT_MODELS[slot.provider];
          data = isTauri()
            ? await transcribeViaTauri(audioFile, slot.key, slot.provider, model, onProgress)
            : await transcribeViaDev(audioFile, slot.key, slot.provider, model, onProgress);
        }

        onProgress?.({ stage: 'processing', progress: 100, message: 'Транскрипция завершена' });
        return processWhisperResponse(data);
      } catch (error) {
        if (error instanceof WhisperError) {
          if (error.code === 'INVALID_KEY') throw error;
          if (error.code === 'RATE_LIMIT') {
            lastError = error;
            triedProviders.add(slot.provider);
            const nextSlot = providerChain.find((s) => !triedProviders.has(s.provider));
            if (nextSlot) {
              const nextName = PROVIDER_NAMES[nextSlot.provider] || nextSlot.provider;
              onProgress?.({
                stage: 'uploading',
                progress: 35,
                message: `${providerName} недоступен — переключение на ${nextName}...`,
              });
            }
            break;
          }
        }
        lastError = error instanceof Error ? error : new Error(String(error));
      }
    }
    triedProviders.add(slot.provider);
  }

  throw new WhisperError(
    `Транскрипция не удалась: ${lastError?.message || 'все провайдеры недоступны'}`,
    'MAX_RETRIES_EXCEEDED',
  );
}

/**
 * Транскрипция через Tauri Rust backend (универсальная команда).
 */
async function transcribeViaTauri(
  audioFile: File | Blob,
  apiKey: string,
  sttProvider: STTProvider,
  model: string,
  onProgress?: (p: TranscriptionProgress) => void,
): Promise<Record<string, unknown>> {
  onProgress?.({ stage: 'uploading', progress: 30, message: 'Отправка на сервер...' });

  const arrayBuffer = await audioFile.arrayBuffer();
  const audioBytes = new Uint8Array(arrayBuffer);
  const filename = audioFile instanceof File ? audioFile.name : 'audio.wav';

  const endpointUrl = `${PROVIDER_BASE_URLS[sttProvider]}/audio/transcriptions`;

  const responseJson = await invoke<string>('call_whisper_compatible_api', {
    endpointUrl,
    audioBytes,
    filename,
    apiKey,
    model,
  }).catch((err: string) => {
    if (err.startsWith('WHISPER_API_ERROR:')) {
      const firstColon = err.indexOf(':');
      const secondColon = err.indexOf(':', firstColon + 1);
      const statusStr = err.slice(firstColon + 1, secondColon);
      const statusCode = parseInt(statusStr, 10);
      const providerName = PROVIDER_NAMES[sttProvider] || sttProvider;
      if (statusCode === 401) throw new WhisperError(`Невалидный API-ключ ${providerName}.`, 'INVALID_KEY');
      if (statusCode === 403) throw new WhisperError(`Доступ запрещён ${providerName}.`, 'RATE_LIMIT');
      if (statusCode === 429) throw new WhisperError('Превышен лимит запросов.', 'RATE_LIMIT');
      if (statusCode >= 500) throw new WhisperError(`Ошибка сервера ${providerName} (${statusCode}).`, 'SERVER_ERROR');
      throw new WhisperError(`Ошибка Whisper API: ${statusCode}`, 'API_ERROR');
    }
    throw new WhisperError(`Ошибка Tauri: ${err}`, 'API_ERROR');
  });

  return JSON.parse(responseJson) as Record<string, unknown>;
}

/**
 * Транскрипция через прямой fetch (только dev-режим).
 */
async function transcribeViaDev(
  audioFile: File | Blob,
  apiKey: string,
  sttProvider: STTProvider,
  model: string,
  onProgress?: (p: TranscriptionProgress) => void,
): Promise<Record<string, unknown>> {
  onProgress?.({ stage: 'uploading', progress: 30, message: 'Отправка на сервер (dev)...' });

  const formData = new FormData();
  formData.append('file', audioFile, audioFile instanceof File ? audioFile.name : 'audio.wav');
  formData.append('model', model);
  formData.append('response_format', 'verbose_json');
  formData.append('language', 'ru');
  formData.append('timestamp_granularities[]', 'segment');

  const devEndpoint = STT_DEV_ENDPOINTS[sttProvider];

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(devEndpoint, {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}` },
      body: formData,
      signal: controller.signal,
    });
  } catch (fetchError) {
    if (fetchError instanceof Error && fetchError.name === 'AbortError') {
      throw new WhisperError('Превышено время ожидания ответа от Whisper API (5 мин).', 'API_ERROR');
    }
    throw fetchError;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const errorBody = await response.text().catch(() => '');
    const statusCode = response.status;
    const providerName = PROVIDER_NAMES[sttProvider] || sttProvider;
    if (statusCode === 401) throw new WhisperError(`Невалидный API-ключ ${providerName}.`, 'INVALID_KEY');
    if (statusCode === 403) throw new WhisperError(`Доступ запрещён ${providerName}.`, 'RATE_LIMIT');
    if (statusCode === 429) throw new WhisperError('Превышен лимит запросов. Повторная попытка...', 'RATE_LIMIT');
    if (statusCode >= 500) throw new WhisperError(`Ошибка сервера ${providerName} (${statusCode}).`, 'SERVER_ERROR');
    throw new WhisperError(
      `Ошибка Whisper API: ${statusCode} — ${errorBody.slice(0, 200)}`,
      'API_ERROR',
    );
  }

  return response.json() as Promise<Record<string, unknown>>;
}

/**
 * Транскрипция через Google Gemini (мультимодальный API).
 * Gemini принимает аудио как base64 и возвращает текст с таймкодами.
 */
async function transcribeViaGemini(
  audioFile: File | Blob,
  apiKey: string,
  onProgress?: (p: TranscriptionProgress) => void,
): Promise<Record<string, unknown>> {
  onProgress?.({ stage: 'uploading', progress: 30, message: 'Отправка в Gemini...' });

  const arrayBuffer = await audioFile.arrayBuffer();
  // Chunk-based base64: избегаем O(n²) конкатенации строк на больших файлах
  const bytes = new Uint8Array(arrayBuffer);
  const CHUNK = 0x8000; // 32KB чанки — безопасно для String.fromCharCode.apply
  const parts: string[] = [];
  for (let i = 0; i < bytes.length; i += CHUNK) {
    parts.push(String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK) as unknown as number[]));
  }
  const base64Audio = btoa(parts.join(''));

  const mimeType = audioFile.type || 'audio/wav';

  const requestBody = {
    contents: [{
      parts: [
        {
          inline_data: {
            mime_type: mimeType,
            data: base64Audio,
          },
        },
        {
          text: 'Транскрибируй это аудио на русском языке. Верни ТОЛЬКО текст транскрипции, без комментариев. Если есть несколько говорящих, отмечай смену говорящего новой строкой.',
        },
      ],
    }],
    generationConfig: {
      temperature: 0.1,
      maxOutputTokens: 8192,
    },
  };

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });
  } catch (fetchError) {
    if (fetchError instanceof Error && fetchError.name === 'AbortError') {
      throw new WhisperError('Превышено время ожидания Gemini (5 мин).', 'API_ERROR');
    }
    throw fetchError;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const statusCode = response.status;
    const errorBody = await response.text().catch(() => '');
    if (statusCode === 401) throw new WhisperError('Невалидный API-ключ Gemini.', 'INVALID_KEY');
    // 403: ключ приостановлен или заблокирован — не INVALID_KEY, а RATE_LIMIT для fallback
    if (statusCode === 403) throw new WhisperError(`Доступ запрещён Gemini (${errorBody.slice(0, 100)}).`, 'RATE_LIMIT');
    if (statusCode === 429) throw new WhisperError('Превышен лимит Gemini.', 'RATE_LIMIT');
    if (statusCode >= 500) throw new WhisperError(`Ошибка сервера Gemini (${statusCode}).`, 'SERVER_ERROR');
    throw new WhisperError(`Ошибка Gemini API: ${statusCode}`, 'API_ERROR');
  }

  const data = await response.json();
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || '';

  if (!text.trim()) {
    throw new WhisperError('Gemini не распознал речь в записи.', 'NO_SPEECH');
  }

  // Конвертируем в формат совместимый с processWhisperResponse
  const lines = text.split('\n').filter((l: string) => l.trim());
  const segments = lines.map((line: string, i: number) => ({
    id: i,
    start: 0,
    end: 0,
    text: line.trim(),
  }));

  return {
    text,
    segments,
    language: 'ru',
    duration: 0,
  };
}

/** Обрабатывает ответ Whisper API — качество и наличие речи. */
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

  // EC-06: Нет речи
  if (!text.trim() || segments.length === 0) {
    throw new WhisperError(
      'В записи не обнаружена речь. Возможно, выбран неверный файл.',
      'NO_SPEECH',
    );
  }

  // EC-05: Оценка качества
  const avgNoSpeechProb =
    segments.reduce((sum, s) => sum + (s.noSpeechProb || 0), 0) / segments.length;
  const avgLogProb =
    segments.reduce((sum, s) => sum + (s.avgLogprob || 0), 0) / segments.length;

  if (avgNoSpeechProb > 0.5) qualityWarnings.push('Высокий уровень шума');
  if (avgLogProb < -1.0) qualityWarnings.push('Низкая уверенность распознавания');

  const lowQualitySegments = segments.filter((s) => (s.noSpeechProb || 0) > 0.7).length;
  const lowQualityPercent = (lowQualitySegments / segments.length) * 100;
  if (lowQualityPercent > 30) {
    qualityWarnings.push(`${lowQualityPercent.toFixed(0)}% записи содержат шум или тишину`);
  }

  return { text, segments, language, duration, qualityWarnings };
}

/** Форматирует таймкод из секунд в MM:SS. */
export function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/** Конвертирует сегменты Whisper в формат стенограммы. */
export function segmentsToTranscript(segments: WhisperSegment[]): string {
  return segments.map((seg) => `[${formatTimestamp(seg.start)}] ${seg.text}`).join('\n');
}

/** Проверяет валидность API-ключа OpenAI. */
export async function validateOpenAIKey(
  apiKey: string,
): Promise<{ valid: boolean; error?: string }> {
  try {
    if (isTauri()) {
      const valid = await invoke<boolean>('validate_openai_key', { apiKey });
      return valid ? { valid: true } : { valid: false, error: 'Невалидный API-ключ' };
    }
    const response = await fetch('/api/openai/v1/models', {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    if (response.ok) return { valid: true };
    if (response.status === 401) return { valid: false, error: 'Невалидный API-ключ' };
    return { valid: false, error: `Ошибка проверки: ${response.status}` };
  } catch {
    return { valid: false, error: 'Нет подключения к API' };
  }
}

export class WhisperError extends Error {
  constructor(
    message: string,
    public code:
      | 'FILE_TOO_LARGE'
      | 'INVALID_KEY'
      | 'RATE_LIMIT'
      | 'SERVER_ERROR'
      | 'API_ERROR'
      | 'NO_SPEECH'
      | 'MAX_RETRIES_EXCEEDED',
  ) {
    super(message);
    this.name = 'WhisperError';
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
