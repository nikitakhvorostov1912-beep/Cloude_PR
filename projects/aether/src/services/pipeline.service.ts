/**
 * Оркестратор AI-пайплайна.
 * Upload → Extract → Transcribe → Generate → Complete
 *
 * Обрабатывает edge cases:
 * EC-05: Плохое качество аудио (предупреждение)
 * EC-06: Нет речи (останов)
 * EC-08: Whisper API retry
 * EC-09: Claude API ошибка (частичный результат)
 * EC-10: Частичный результат (показать что есть)
 * EC-11: Невалидный JSON (автоисправление)
 * EC-12: Пустой артефакт (серая карточка)
 */

import type { ArtifactType } from '@/types/artifact.types';
import type { LLMProvider, STTProvider, APIKeys, ProviderRoutingMode } from '@/types/api.types';
import type { PipelineStage, StageStatus } from '@/types/pipeline.types';
import { PROVIDER_NAMES, DEFAULT_STT_MODELS } from '@/lib/constants';
import { transcribeAudio, segmentsToTranscript, type WhisperResult } from './whisper.service';
import { generateArtifacts, type LLMResult } from './llm.service';
import { buildAllPrompts, type PromptContext } from '@/lib/prompts';
import { validateArtifactSchema } from '@/lib/validators';
import { validatePipelineConfig, validateAudioFile } from '@/lib/schemas';
import { checkRateLimitWarnings } from '@/lib/rate-limiter';
import { estimateChunking, chunkTranscript } from '@/lib/chunking';
import { estimateTotalCost, type CostBreakdown } from '@/lib/cost-estimator';
import { distributeAcrossProviders, resetBlockedProviders } from '@/lib/provider-router';

export interface PipelineConfig {
  meetingId: string;
  projectName: string;
  meetingDate: string;
  meetingType: string;
  artifactTypes: ArtifactType[];
  provider: LLMProvider;
  /** Кастомная модель (если пустая — DEFAULT_LLM_MODELS[provider]) */
  llmModel?: string;
  sttProvider: STTProvider;
  apiKeys: APIKeys;
  /** Предыдущие артефакты для кумулятивной логики */
  previousArtifacts?: Record<string, string>;
  /** Режим маршрутизации провайдеров */
  routingMode?: ProviderRoutingMode;
}

/** Входной файл для multi-file пайплайна */
export interface PipelineInputFile {
  file: File;
  fileId: string;
  order: number;
  label: string;
  /** Нативный путь на диске — для больших файлов (не грузятся в память) */
  nativePath?: string;
}

export interface PipelineCallbacks {
  onStageChange: (stage: PipelineStage) => void;
  onProgress: (progress: number) => void;
  onStreamingText: (text: string) => void;
  onError: (error: string) => void;
  onCostEstimate: (cost: number) => void;
  onQualityWarnings: (warnings: string[]) => void;
  onArtifactComplete: (type: ArtifactType, data: Record<string, unknown> | null, isEmpty: boolean) => void;
  onArtifactError: (type: ArtifactType, error: string) => void;
  /** Прогресс обработки отдельного файла */
  onFileProgress: (fileId: string, progress: number, status: StageStatus, error: string | null) => void;
}

export interface PipelineOptions {
  /** AbortSignal для отмены пайплайна */
  signal?: AbortSignal;
}

export interface PipelineResult {
  success: boolean;
  /** Результат Whisper первого успешного файла (обратная совместимость) */
  transcript: WhisperResult | null;
  /** Объединённый текст транскрипции всех файлов */
  mergedTranscript: string;
  artifacts: Map<ArtifactType, ArtifactResult>;
  costBreakdown: CostBreakdown | null;
  qualityWarnings: string[];
  errors: string[];
}

export interface ArtifactResult {
  type: ArtifactType;
  data: Record<string, unknown> | null;
  rawText: string;
  isEmpty: boolean;
  error: string | null;
  tokensUsed: number;
  model: string;
}

/** Маппинг LLM-провайдер → поле APIKeys */
const LLM_KEY_MAP: Record<LLMProvider, keyof APIKeys> = {
  claude: 'claudeKey',
  openai: 'openaiKey',
  gemini: 'geminiKey',
  groq: 'groqKey',
  deepseek: 'deepseekKey',
  mimo: 'mimoKey',
  cerebras: 'cerebrasKey',
  mistral: 'mistralKey',
  openrouter: 'openrouterKey',
};

/** Маппинг STT-провайдер → поле APIKeys */
const STT_KEY_MAP: Record<STTProvider, keyof APIKeys> = {
  openai: 'openaiKey',
  groq: 'groqKey',
  gemini: 'geminiKey',
};

/** Получить API-ключ для LLM-провайдера. */
function getKeyForLLM(provider: LLMProvider, keys: APIKeys): string {
  return keys[LLM_KEY_MAP[provider]];
}

/** Получить API-ключ для STT-провайдера. */
function getKeyForSTT(sttProvider: STTProvider, keys: APIKeys): string {
  return keys[STT_KEY_MAP[sttProvider]];
}

/**
 * Объединяет транскрипции нескольких файлов в единый текст.
 * При одном файле — текст как есть. При N — разделители с именами файлов.
 */
function mergeTranscripts(
  transcripts: Array<{ label: string; text: string; order: number }>,
): string {
  if (transcripts.length === 0) return '';
  if (transcripts.length === 1) return transcripts[0].text;

  const sorted = [...transcripts].sort((a, b) => a.order - b.order);
  const total = sorted.length;

  return sorted
    .map((t, i) => `--- Запись ${i + 1} из ${total}: ${t.label} ---\n${t.text}`)
    .join('\n\n');
}

/**
 * Запускает полный AI-пайплайн обработки записей (multi-file).
 * Обрабатывает несколько файлов последовательно, объединяет транскрипции,
 * генерирует артефакты по объединённому тексту.
 *
 * Partial success: если хотя бы 1 файл транскрибирован — продолжаем генерацию.
 */
export async function runPipeline(
  audioFiles: PipelineInputFile[],
  config: PipelineConfig,
  callbacks: PipelineCallbacks,
  options?: PipelineOptions,
): Promise<PipelineResult> {
  const result: PipelineResult = {
    success: false,
    transcript: null,
    mergedTranscript: '',
    artifacts: new Map(),
    costBreakdown: null,
    qualityWarnings: [],
    errors: [],
  };

  try {
    // Ранняя проверка: 0 файлов
    if (audioFiles.length === 0) {
      throw new PipelineError('Не выбрано ни одного файла для обработки.', 'upload');
    }

    // Сортируем по order
    const sortedFiles = [...audioFiles].sort((a, b) => a.order - b.order);

    // === Stage 1: Upload (валидация всех файлов) ===
    callbacks.onStageChange('upload');
    callbacks.onProgress(5);
    callbacks.onStreamingText(
      `Подготовка ${sortedFiles.length} файл(ов) к обработке...\n`,
    );

    // Валидация конфигурации
    const configValidation = validatePipelineConfig(config);
    if (!configValidation.success) {
      throw new PipelineError(
        `Некорректная конфигурация: ${configValidation.errors?.join('; ')}`,
        'upload',
      );
    }

    // Валидация API-ключей
    const sttKey = getKeyForSTT(config.sttProvider, config.apiKeys);
    if (!sttKey) {
      const sttName = PROVIDER_NAMES[config.sttProvider] || config.sttProvider;
      throw new PipelineError(`Не указан API-ключ ${sttName} (требуется для транскрипции).`, 'upload');
    }

    const llmKey = getKeyForLLM(config.provider, config.apiKeys);
    if (!llmKey) {
      const llmName = PROVIDER_NAMES[config.provider] || config.provider;
      throw new PipelineError(
        `Не указан API-ключ ${llmName} (требуется для генерации артефактов).`,
        'upload',
      );
    }

    // Валидация каждого файла (однократная)
    const validFileIds = new Set<string>();
    for (const inputFile of sortedFiles) {
      callbacks.onFileProgress(inputFile.fileId, 0, 'active', null);

      const fileValidation = validateAudioFile(inputFile.file);
      if (!fileValidation.valid) {
        callbacks.onFileProgress(inputFile.fileId, 0, 'error', fileValidation.error!);
        callbacks.onStreamingText(`✗ ${inputFile.label}: ${fileValidation.error}\n`);
        result.errors.push(`${inputFile.label}: ${fileValidation.error}`);
      } else {
        validFileIds.add(inputFile.fileId);
        callbacks.onFileProgress(inputFile.fileId, 10, 'active', null);
        callbacks.onStreamingText(`✓ ${inputFile.label}: валидация пройдена\n`);
      }
    }

    // Отфильтруем файлы, прошедшие валидацию
    const validFiles = sortedFiles.filter((f) => validFileIds.has(f.fileId));

    if (validFiles.length === 0) {
      throw new PipelineError('Ни один файл не прошёл валидацию.', 'upload');
    }

    callbacks.onProgress(10);

    // Проверка отмены
    if (options?.signal?.aborted) {
      throw new PipelineError('Обработка отменена пользователем.', 'upload');
    }

    // === Stage 2: Extract Audio (для каждого файла) ===
    callbacks.onStageChange('extract');
    callbacks.onProgress(15);
    callbacks.onStreamingText(`\nИзвлечение аудиодорожек (${validFiles.length} файлов)...\n`);

    const extractedFiles: Array<{ inputFile: PipelineInputFile; blob: Blob }> = [];

    for (let i = 0; i < validFiles.length; i++) {
      const inputFile = validFiles[i];
      callbacks.onFileProgress(inputFile.fileId, 20, 'active', null);
      callbacks.onStreamingText(`  Извлечение: ${inputFile.label}...\n`);

      try {
        const audioBlob = await extractAudio(inputFile.file, inputFile.nativePath);
        extractedFiles.push({ inputFile, blob: audioBlob });
        callbacks.onFileProgress(inputFile.fileId, 30, 'active', null);
        callbacks.onStreamingText(`  ✓ ${inputFile.label}: аудио подготовлено\n`);
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Ошибка извлечения';
        callbacks.onFileProgress(inputFile.fileId, 0, 'error', errMsg);
        callbacks.onStreamingText(`  ✗ ${inputFile.label}: ${errMsg}\n`);
        result.errors.push(`${inputFile.label}: ${errMsg}`);
        // Продолжаем с остальными файлами
      }

      // Прогресс в рамках стадии extract (15-25)
      const extractProgress = 15 + ((i + 1) / validFiles.length) * 10;
      callbacks.onProgress(extractProgress);
    }

    if (extractedFiles.length === 0) {
      throw new PipelineError('Ни один файл не удалось подготовить для транскрипции.', 'extract');
    }

    callbacks.onProgress(25);

    // Проверка отмены
    if (options?.signal?.aborted) {
      throw new PipelineError('Обработка отменена пользователем.', 'extract');
    }

    // === Stage 3: Transcribe (каждый файл последовательно) ===
    callbacks.onStageChange('transcribe');
    callbacks.onProgress(30);
    callbacks.onStreamingText(
      `\nЗапуск транскрипции ${extractedFiles.length} файлов через Whisper API...\n`,
    );

    const transcribedResults: Array<{
      inputFile: PipelineInputFile;
      whisperResult: WhisperResult;
      text: string;
    }> = [];

    for (let i = 0; i < extractedFiles.length; i++) {
      const { inputFile, blob } = extractedFiles[i];
      callbacks.onFileProgress(inputFile.fileId, 40, 'active', null);
      callbacks.onStreamingText(`\n  Транскрипция: ${inputFile.label}...\n`);

      try {
        const whisperResult = await transcribeAudio(blob, sttKey, config.sttProvider, (p) => {
          // Прогресс файла: 40-90
          const fileProgress = 40 + (p.progress / 100) * 50;
          callbacks.onFileProgress(inputFile.fileId, fileProgress, 'active', null);
          callbacks.onStreamingText(`    ${p.message}\n`);
        }, config.apiKeys as unknown as Record<string, string>);

        // EC-05: Предупреждения о качестве
        if (whisperResult.qualityWarnings.length > 0) {
          result.qualityWarnings.push(
            ...whisperResult.qualityWarnings.map((w) => `${inputFile.label}: ${w}`),
          );
          callbacks.onStreamingText(
            `  ⚠ ${inputFile.label}: ${whisperResult.qualityWarnings.join(', ')}\n`,
          );
        }

        const text = segmentsToTranscript(whisperResult.segments);

        // Пустая транскрипция — пропускаем, но не ошибка
        if (!text.trim()) {
          callbacks.onFileProgress(inputFile.fileId, 100, 'completed', null);
          callbacks.onStreamingText(
            `  ○ ${inputFile.label}: речь не распознана, пропускаем\n`,
          );
          continue;
        }

        transcribedResults.push({ inputFile, whisperResult, text });

        // Сохраняем первый успешный результат для обратной совместимости
        if (result.transcript === null) {
          result.transcript = whisperResult;
        }

        callbacks.onFileProgress(inputFile.fileId, 100, 'completed', null);
        callbacks.onStreamingText(
          `  ✓ ${inputFile.label}: ${whisperResult.segments.length} сегментов\n`,
        );
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Ошибка транскрипции';
        callbacks.onFileProgress(inputFile.fileId, 0, 'error', errMsg);
        callbacks.onStreamingText(`  ✗ ${inputFile.label}: ${errMsg}\n`);
        result.errors.push(`${inputFile.label}: ${errMsg}`);
        // Продолжаем с остальными файлами
      }

      // Прогресс в рамках стадии transcribe (30-55)
      const transcribeProgress = 30 + ((i + 1) / extractedFiles.length) * 25;
      callbacks.onProgress(transcribeProgress);
    }

    // EC-06: Проверка — хотя бы один файл транскрибирован (partial success)
    if (transcribedResults.length === 0) {
      throw new PipelineError(
        'Транскрипция пуста — речь не распознана ни в одном файле. Проверьте файлы и качество записи.',
        'transcribe',
      );
    }

    // Предупреждения о качестве (сводные)
    if (result.qualityWarnings.length > 0) {
      callbacks.onQualityWarnings(result.qualityWarnings);
    }

    // Объединяем транскрипции
    const mergedTranscript = mergeTranscripts(
      transcribedResults.map((r) => ({
        label: r.inputFile.label,
        text: r.text,
        order: r.inputFile.order,
      })),
    );
    result.mergedTranscript = mergedTranscript;

    callbacks.onStreamingText(
      `\nТранскрипция завершена: ${transcribedResults.length}/${extractedFiles.length} файлов обработано\n`,
    );
    callbacks.onProgress(55);

    // Проверка отмены
    if (options?.signal?.aborted) {
      throw new PipelineError('Обработка отменена пользователем.', 'transcribe');
    }

    // Проверка чанкинга
    const chunkingInfo = estimateChunking(mergedTranscript);
    if (chunkingInfo.needsChunking) {
      callbacks.onStreamingText(
        `\n📊 Длинная запись: ${chunkingInfo.totalTokens} токенов, разбивка на ${chunkingInfo.chunkCount} частей\n`,
      );
    }

    // === Stage 4: Generate Artifacts ===
    callbacks.onStageChange('generate');
    callbacks.onProgress(60);

    // Оценка стоимости (используем суммарную длительность)
    const totalDuration = transcribedResults.reduce(
      (sum, r) => sum + r.whisperResult.duration,
      0,
    );
    const costEstimate = estimateTotalCost(
      totalDuration,
      mergedTranscript,
      config.artifactTypes.length,
      config.provider,
    );
    result.costBreakdown = costEstimate;
    callbacks.onCostEstimate(costEstimate.totalCost);
    callbacks.onStreamingText(
      `\n💰 Стоимость обработки: ~$${costEstimate.totalCost.toFixed(2)}\n`,
    );

    // Проверка rate limit (предупреждение, не блокировка)
    const rateLimitWarnings = checkRateLimitWarnings();
    if (rateLimitWarnings.length > 0) {
      callbacks.onStreamingText(`\n⚠ Предупреждение об использовании API:\n`);
      rateLimitWarnings.forEach((w) => callbacks.onStreamingText(`  ${w}\n`));
      callbacks.onStreamingText('\n');
    }

    // Чанкинг длинных транскриптов — обрабатываем ВСЕ чанки через Map-Reduce
    const chunks = chunkTranscript(mergedTranscript);
    let effectiveTranscript: string;

    if (chunks.length > 1) {
      callbacks.onStreamingText(
        `\n📊 Длинная запись: разбивка на ${chunks.length} частей, объединение результатов (Map-Reduce)\n`,
      );
      // Объединяем чанки с пометкой позиции для LLM
      effectiveTranscript = chunks.map((chunk, i) =>
        `=== ЧАСТЬ ${i + 1} из ${chunks.length} ===\n${chunk}`
      ).join('\n\n');
    } else {
      effectiveTranscript = mergedTranscript;
    }

    // Формируем контекст для промптов
    const promptContext: PromptContext = {
      meetingType: config.meetingType,
      projectName: config.projectName,
      meetingDate: config.meetingDate,
      transcript: effectiveTranscript,
      previousArtifacts: config.previousArtifacts,
    };

    // Строим промпты для выбранных типов артефактов (без transcript — он уже готов)
    const artifactTypesForLLM = config.artifactTypes.filter((t) => t !== 'transcript');
    const prompts = buildAllPrompts(artifactTypesForLLM, promptContext);

    // Сброс блокировок провайдеров перед новым запуском
    resetBlockedProviders();

    // Auto-routing: распределяем артефакты по провайдерам (fan-out)
    const routingMode = config.routingMode ?? 'auto';
    const providerSlots = routingMode === 'auto'
      ? distributeAcrossProviders(prompts.length, config.apiKeys, config.provider)
      : undefined;

    if (routingMode === 'auto' && providerSlots && providerSlots.length > 0) {
      const uniqueProviders = [...new Set(providerSlots.map((s) => s.provider))];
      const providerNames = uniqueProviders.map((p) => PROVIDER_NAMES[p] || p).join(', ');
      callbacks.onStreamingText(
        `\n⚡ Auto-routing: ${prompts.length} артефактов через ${uniqueProviders.length} провайдеров (${providerNames})\n`,
      );
      if (uniqueProviders.length > 1) {
        callbacks.onStreamingText(`   Параллельная генерация — до ${Math.min(4, uniqueProviders.length)}x ускорение\n`);
      }
    } else {
      const llmName = PROVIDER_NAMES[config.provider] || config.provider;
      callbacks.onStreamingText(
        `\nГенерация ${prompts.length} артефактов через ${llmName}...\n`,
      );
    }

    callbacks.onStreamingText('\n');

    // Запускаем генерацию (с fan-out если auto-routing)
    await generateArtifacts(prompts, llmKey, config.provider, {
      onArtifactStart: (type) => {
        callbacks.onStreamingText(`▶ ${type}...\n`);
      },
      onArtifactComplete: (type, llmResult) => {
        processArtifactResult(type, llmResult, result, callbacks);

        // Обновляем прогресс
        const completedCount = result.artifacts.size;
        const totalCount = config.artifactTypes.length;
        const progressInStage = (completedCount / totalCount) * 30;
        callbacks.onProgress(60 + progressInStage);
      },
      onArtifactError: (type, error) => {
        // EC-10: Частичный результат — сохраняем что есть
        const errMsg = error.message;
        result.artifacts.set(type, {
          type,
          data: null,
          rawText: '',
          isEmpty: true,
          error: errMsg,
          tokensUsed: 0,
          model: '',
        });
        result.errors.push(`${type}: ${errMsg}`);
        callbacks.onArtifactError(type, errMsg);
        callbacks.onStreamingText(`✗ ${type}: ${errMsg}\n`);
      },
      onToken: (_type, token) => {
        callbacks.onStreamingText(token.slice(0, 100) + (token.length > 100 ? '...' : '') + '\n');
      },
      onProgress: (message) => {
        callbacks.onStreamingText(`  ${message}\n`);
      },
    }, config.llmModel, providerSlots, config.apiKeys);

    console.log('[Pipeline] generateArtifacts done. Result artifacts:', [...result.artifacts.entries()].map(([k, v]) => ({ type: k, hasData: !!v.data, isEmpty: v.isEmpty, error: v.error })));

    // Если transcript был в списке — добавляем его как готовый артефакт
    // Используем первый успешный whisperResult для обратной совместимости
    if (config.artifactTypes.includes('transcript') && result.transcript) {
      const firstWhisper = result.transcript;
      const transcriptArtifact: ArtifactResult = {
        type: 'transcript',
        data: {
          formatted_transcript: firstWhisper.segments.map((seg) => ({
            timestamp: formatTimecode(seg.start),
            speaker: seg.speaker || 'Участник',
            text: seg.text,
            topics: [],
          })),
          chapters: [],
          statistics: {
            total_duration_minutes: Math.round(totalDuration / 60),
            speakers_count: 1,
            speaker_time: {},
            topics_discussed: [],
            dominant_speaker: '',
          },
        },
        rawText: mergedTranscript,
        isEmpty: false,
        error: null,
        tokensUsed: 0,
        model: DEFAULT_STT_MODELS[config.sttProvider],
      };

      result.artifacts.set('transcript', transcriptArtifact);
      callbacks.onArtifactComplete('transcript', transcriptArtifact.data, false);
      callbacks.onStreamingText('✓ transcript (Whisper)\n');
    }

    // === Stage 5: Complete ===
    callbacks.onStageChange('complete');
    callbacks.onProgress(100);

    const successCount = [...result.artifacts.values()].filter((a) => !a.error).length;
    const errorCount = [...result.artifacts.values()].filter((a) => a.error).length;

    callbacks.onStreamingText(
      `\n═══════════════════════════════\n` +
      `Обработка завершена: ${successCount} артефактов готово` +
      (errorCount > 0 ? `, ${errorCount} с ошибками` : '') +
      `\n═══════════════════════════════\n`,
    );

    result.success = successCount > 0;
    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Неизвестная ошибка';
    result.errors.push(message);
    callbacks.onError(message);
    callbacks.onStreamingText(`\n❌ Ошибка: ${message}\n`);
    return result;
  }
}

/**
 * Обработка результата генерации одного артефакта.
 */
function processArtifactResult(
  type: ArtifactType,
  llmResult: LLMResult,
  pipelineResult: PipelineResult,
  callbacks: PipelineCallbacks,
): void {
  console.log('[Pipeline:processArtifactResult]', {
    type,
    hasData: !!llmResult.data,
    parseError: llmResult.parseError,
    textLength: llmResult.text.length,
    tokensUsed: llmResult.tokensUsed.total,
    model: llmResult.model,
  });
  // EC-11: Проверка парсинга JSON
  if (llmResult.parseError) {
    callbacks.onStreamingText(`⚠ ${type}: JSON не распознан, показан сырой результат\n`);
    pipelineResult.artifacts.set(type, {
      type,
      data: null,
      rawText: llmResult.text,
      isEmpty: false,
      error: `Не удалось структурировать: ${llmResult.parseError}`,
      tokensUsed: llmResult.tokensUsed.total,
      model: llmResult.model,
    });
    callbacks.onArtifactComplete(type, null, false);
    return;
  }

  // EC-12: Проверка на пустой артефакт
  const validation = validateArtifactSchema(type, llmResult.data);
  const isEmpty = validation.isEmpty;

  if (isEmpty) {
    callbacks.onStreamingText(`○ ${type}: пусто (нет данных этого типа на встрече)\n`);
  } else {
    callbacks.onStreamingText(`✓ ${type} (${llmResult.tokensUsed.total} токенов)\n`);
  }

  pipelineResult.artifacts.set(type, {
    type,
    data: llmResult.data,
    rawText: llmResult.text,
    isEmpty,
    error: null,
    tokensUsed: llmResult.tokensUsed.total,
    model: llmResult.model,
  });

  callbacks.onArtifactComplete(type, llmResult.data, isEmpty);
}

/**
 * Извлечение аудио из файла.
 * Видео/большие файлы конвертируются через ffmpeg (Tauri) → MP3 mono 16kHz (~0.5 МБ/мин).
 * Аудио <= 25 МБ передаётся напрямую.
 *
 * @param file — File объект (может быть пустым placeholder)
 * @param nativePath — нативный путь на диске (приоритет для больших файлов)
 */
/** Проверка Tauri окружения */
const isTauri = (): boolean => '__TAURI_INTERNALS__' in window;

async function extractAudio(file: File, nativePath?: string): Promise<Blob> {
  const sizeMb = file.size / (1024 * 1024);
  const isVideo = file.type.startsWith('video/') || /\.(mp4|mkv|avi|mov|webm|flv|wmv)$/i.test(file.name);

  // Аудио <= 25 МБ без nativePath — как есть
  if (!isVideo && sizeMb <= 25 && !nativePath) {
    return file;
  }

  // В браузерном dev-режиме (без Tauri) — ffmpeg недоступен
  if (!isTauri()) {
    if (sizeMb <= 25) return file;
    throw new PipelineError(
      `Файл ${file.name} (${sizeMb.toFixed(0)} МБ) требует ffmpeg. Запустите через «npm run tauri dev».`,
      'extract',
    );
  }

  try {
    const { invoke } = await import('@tauri-apps/api/core');

    // Приоритет: path-based (не грузит файл в память)
    if (nativePath) {
      const raw = await invoke<number[] | Uint8Array>('extract_audio_from_path', {
        inputPath: nativePath,
      });
      // Tauri 2 возвращает Vec<u8> как number[] — нужен Uint8Array для Blob
      const bytes = raw instanceof Uint8Array ? raw : new Uint8Array(raw);
      return new Blob([bytes], { type: 'audio/mpeg' });
    }

    // Fallback: byte-based (только для маленьких файлов без nativePath)
    const arrayBuffer = await file.arrayBuffer();
    const inputBytes = new Uint8Array(arrayBuffer);

    const raw = await invoke<number[] | Uint8Array>('extract_audio_ffmpeg', {
      inputBytes,
      filename: file.name,
    });
    // Tauri 2 возвращает Vec<u8> как number[] — нужен Uint8Array для Blob
    const bytes = raw instanceof Uint8Array ? raw : new Uint8Array(raw);
    return new Blob([bytes], { type: 'audio/mpeg' });
  } catch (err) {
    // Fallback: если ffmpeg недоступен и файл <= 25 МБ
    if (sizeMb <= 25 && !nativePath) return file;

    const msg = err instanceof Error ? err.message : String(err);
    throw new PipelineError(
      `Не удалось извлечь аудио (${file.name}): ${msg}`,
      'extract',
    );
  }
}

/**
 * Форматирует таймкод из секунд в HH:MM:SS.
 */
function formatTimecode(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

/** Ошибка пайплайна с указанием стадии */
export class PipelineError extends Error {
  constructor(
    message: string,
    public stage: PipelineStage,
  ) {
    super(message);
    this.name = 'PipelineError';
  }
}
