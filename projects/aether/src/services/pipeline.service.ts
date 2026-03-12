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
import type { LLMProvider } from '@/types/api.types';
import type { PipelineStage } from '@/types/pipeline.types';
import { transcribeAudio, segmentsToTranscript, type WhisperResult } from './whisper.service';
import { generateArtifacts, type LLMResult } from './llm.service';
import { buildAllPrompts, type PromptContext } from '@/lib/prompts';
import { validateArtifactSchema } from '@/lib/validators';
import { estimateChunking } from '@/lib/chunking';
import { estimateTotalCost, type CostBreakdown } from '@/lib/cost-estimator';

export interface PipelineConfig {
  meetingId: string;
  projectName: string;
  meetingDate: string;
  meetingType: string;
  artifactTypes: ArtifactType[];
  provider: LLMProvider;
  apiKeys: {
    openaiKey: string;
    claudeKey: string;
  };
  /** Предыдущие артефакты для кумулятивной логики */
  previousArtifacts?: Record<string, string>;
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
}

export interface PipelineResult {
  success: boolean;
  transcript: WhisperResult | null;
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

/**
 * Запускает полный AI-пайплайн обработки записи.
 */
export async function runPipeline(
  audioFile: File,
  config: PipelineConfig,
  callbacks: PipelineCallbacks,
): Promise<PipelineResult> {
  const result: PipelineResult = {
    success: false,
    transcript: null,
    artifacts: new Map(),
    costBreakdown: null,
    qualityWarnings: [],
    errors: [],
  };

  try {
    // === Stage 1: Upload ===
    callbacks.onStageChange('upload');
    callbacks.onProgress(5);
    callbacks.onStreamingText('Подготовка файла к обработке...\n');

    // Валидация API-ключей
    if (!config.apiKeys.openaiKey) {
      throw new PipelineError('Не указан API-ключ OpenAI (требуется для транскрипции).', 'upload');
    }

    const llmKey = config.provider === 'claude' ? config.apiKeys.claudeKey : config.apiKeys.openaiKey;
    if (!llmKey) {
      throw new PipelineError(
        `Не указан API-ключ ${config.provider === 'claude' ? 'Claude' : 'OpenAI'} (требуется для генерации артефактов).`,
        'upload',
      );
    }

    callbacks.onProgress(10);

    // === Stage 2: Extract Audio ===
    callbacks.onStageChange('extract');
    callbacks.onProgress(15);
    callbacks.onStreamingText('Извлечение аудиодорожки...\n');

    // В Tauri: вызов ffmpeg через Tauri command
    // В dev: используем файл как есть (пропускаем ffmpeg)
    const audioBlob = await extractAudio(audioFile);
    callbacks.onProgress(25);
    callbacks.onStreamingText('Аудио подготовлено.\n');

    // === Stage 3: Transcribe ===
    callbacks.onStageChange('transcribe');
    callbacks.onProgress(30);
    callbacks.onStreamingText('Запуск транскрипции через Whisper API...\n');

    const whisperResult = await transcribeAudio(audioBlob, config.apiKeys.openaiKey, (p) => {
      callbacks.onProgress(30 + (p.progress / 100) * 25);
      callbacks.onStreamingText(`${p.message}\n`);
    });

    result.transcript = whisperResult;
    callbacks.onProgress(55);

    // EC-05: Предупреждения о качестве
    if (whisperResult.qualityWarnings.length > 0) {
      result.qualityWarnings = whisperResult.qualityWarnings;
      callbacks.onQualityWarnings(whisperResult.qualityWarnings);
      callbacks.onStreamingText(
        `\n⚠ Предупреждение: ${whisperResult.qualityWarnings.join(', ')}\n`,
      );
    }

    const transcriptText = segmentsToTranscript(whisperResult.segments);
    callbacks.onStreamingText(`\nТранскрипция завершена: ${whisperResult.segments.length} сегментов\n`);

    // Проверка чанкинга
    const chunkingInfo = estimateChunking(transcriptText);
    if (chunkingInfo.needsChunking) {
      callbacks.onStreamingText(
        `\n📊 Длинная запись: ${chunkingInfo.totalTokens} токенов, разбивка на ${chunkingInfo.chunkCount} частей\n`,
      );
    }

    // === Stage 4: Generate Artifacts ===
    callbacks.onStageChange('generate');
    callbacks.onProgress(60);

    // Оценка стоимости
    const costEstimate = estimateTotalCost(
      whisperResult.duration,
      transcriptText,
      config.artifactTypes.length,
      config.provider,
    );
    result.costBreakdown = costEstimate;
    callbacks.onCostEstimate(costEstimate.totalCost);
    callbacks.onStreamingText(
      `\n💰 Стоимость обработки: ~$${costEstimate.totalCost.toFixed(2)}\n`,
    );

    // Формируем контекст для промптов
    const promptContext: PromptContext = {
      meetingType: config.meetingType,
      projectName: config.projectName,
      meetingDate: config.meetingDate,
      transcript: transcriptText,
      previousArtifacts: config.previousArtifacts,
    };

    // Строим промпты для выбранных типов артефактов (без transcript — он уже готов)
    const artifactTypesForLLM = config.artifactTypes.filter((t) => t !== 'transcript');
    const prompts = buildAllPrompts(artifactTypesForLLM, promptContext);

    callbacks.onStreamingText(
      `\nГенерация ${prompts.length} артефактов через ${config.provider === 'claude' ? 'Claude' : 'OpenAI'}...\n\n`,
    );

    // Запускаем генерацию
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
    });

    // Если transcript был в списке — добавляем его как готовый артефакт
    if (config.artifactTypes.includes('transcript')) {
      const transcriptArtifact: ArtifactResult = {
        type: 'transcript',
        data: {
          formatted_transcript: whisperResult.segments.map((seg) => ({
            timestamp: formatTimecode(seg.start),
            speaker: seg.speaker || 'Участник',
            text: seg.text,
            topics: [],
          })),
          chapters: [],
          statistics: {
            total_duration_minutes: Math.round(whisperResult.duration / 60),
            speakers_count: 1,
            speaker_time: {},
            topics_discussed: [],
            dominant_speaker: '',
          },
        },
        rawText: transcriptText,
        isEmpty: false,
        error: null,
        tokensUsed: 0,
        model: 'whisper-1',
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
 * В Tauri: использует ffmpeg через Tauri command.
 * В dev-режиме: возвращает файл как есть.
 */
async function extractAudio(file: File): Promise<Blob> {
  const isTauri = '__TAURI_INTERNALS__' in window;

  if (isTauri) {
    // TODO: Tauri command для ffmpeg extract + normalize
    // invoke('extract_audio', { filePath: file.path, outputPath: ... })
    return file;
  }

  // Dev-режим: возвращаем файл как есть
  // Для аудиофайлов — используем напрямую
  // Для видео — нужен ffmpeg (в Tauri)
  return file;
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
