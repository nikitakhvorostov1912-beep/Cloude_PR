/**
 * Оценка стоимости API-вызовов.
 * Цены актуальны на март 2026.
 */

import type { LLMProvider } from '@/types/api.types';
import { estimateTokens } from './chunking';

/** Цены Whisper API: $0.006 за минуту */
const WHISPER_PRICE_PER_MINUTE = 0.006;

/** Цены Claude Sonnet 4: $3 / 1M input, $15 / 1M output */
const CLAUDE_INPUT_PRICE_PER_TOKEN = 3.0 / 1_000_000;
const CLAUDE_OUTPUT_PRICE_PER_TOKEN = 15.0 / 1_000_000;

/** Цены GPT-4o: $2.50 / 1M input, $10 / 1M output */
const GPT4O_INPUT_PRICE_PER_TOKEN = 2.50 / 1_000_000;
const GPT4O_OUTPUT_PRICE_PER_TOKEN = 10.0 / 1_000_000;

/** Средний размер ответа на один артефакт (токены) */
const AVG_OUTPUT_TOKENS_PER_ARTIFACT = 3_000;

/** Размер системного промпта (токены) */
const SYSTEM_PROMPT_TOKENS = 500;

export interface CostBreakdown {
  whisperCost: number;
  llmInputCost: number;
  llmOutputCost: number;
  totalCost: number;
  details: {
    whisperMinutes: number;
    inputTokens: number;
    outputTokens: number;
    provider: LLMProvider;
    artifactCount: number;
  };
}

/**
 * Оценка стоимости транскрипции через Whisper API.
 */
export function estimateWhisperCost(durationSeconds: number): number {
  const minutes = durationSeconds / 60;
  return minutes * WHISPER_PRICE_PER_MINUTE;
}

/**
 * Оценка стоимости генерации артефактов через LLM.
 */
export function estimateLLMCost(
  transcriptText: string,
  artifactCount: number,
  provider: LLMProvider,
): { inputCost: number; outputCost: number } {
  const transcriptTokens = estimateTokens(transcriptText);

  // Каждый артефакт получает полный транскрипт + системный промпт
  const totalInputTokens = (transcriptTokens + SYSTEM_PROMPT_TOKENS) * artifactCount;
  const totalOutputTokens = AVG_OUTPUT_TOKENS_PER_ARTIFACT * artifactCount;

  const inputPrice = provider === 'claude' ? CLAUDE_INPUT_PRICE_PER_TOKEN : GPT4O_INPUT_PRICE_PER_TOKEN;
  const outputPrice = provider === 'claude' ? CLAUDE_OUTPUT_PRICE_PER_TOKEN : GPT4O_OUTPUT_PRICE_PER_TOKEN;

  return {
    inputCost: totalInputTokens * inputPrice,
    outputCost: totalOutputTokens * outputPrice,
  };
}

/**
 * Полная оценка стоимости обработки одной записи.
 */
export function estimateTotalCost(
  durationSeconds: number,
  transcriptText: string,
  artifactCount: number,
  provider: LLMProvider,
): CostBreakdown {
  const whisperCost = estimateWhisperCost(durationSeconds);
  const { inputCost, outputCost } = estimateLLMCost(transcriptText, artifactCount, provider);
  const transcriptTokens = estimateTokens(transcriptText);

  return {
    whisperCost,
    llmInputCost: inputCost,
    llmOutputCost: outputCost,
    totalCost: whisperCost + inputCost + outputCost,
    details: {
      whisperMinutes: durationSeconds / 60,
      inputTokens: (transcriptTokens + SYSTEM_PROMPT_TOKENS) * artifactCount,
      outputTokens: AVG_OUTPUT_TOKENS_PER_ARTIFACT * artifactCount,
      provider,
      artifactCount,
    },
  };
}

/**
 * Быстрая оценка стоимости ДО транскрипции (только по длительности).
 * Используется для отображения "~$X.XX" перед началом обработки.
 */
export function estimateCostBeforeProcessing(
  durationSeconds: number,
  artifactCount: number,
  provider: LLMProvider,
): number {
  const whisperCost = estimateWhisperCost(durationSeconds);

  // Грубая оценка: ~150 слов/минута, ~2.5 символа/токен для русского
  const estimatedWords = (durationSeconds / 60) * 150;
  const estimatedChars = estimatedWords * 6; // ~6 символов на русское слово
  const estimatedTokens = estimatedChars / 2.5;

  const inputPrice = provider === 'claude' ? CLAUDE_INPUT_PRICE_PER_TOKEN : GPT4O_INPUT_PRICE_PER_TOKEN;
  const outputPrice = provider === 'claude' ? CLAUDE_OUTPUT_PRICE_PER_TOKEN : GPT4O_OUTPUT_PRICE_PER_TOKEN;

  const llmCost =
    (estimatedTokens + SYSTEM_PROMPT_TOKENS) * artifactCount * inputPrice +
    AVG_OUTPUT_TOKENS_PER_ARTIFACT * artifactCount * outputPrice;

  return whisperCost + llmCost;
}

/**
 * Форматирование стоимости для отображения.
 */
export function formatCost(usd: number): string {
  if (usd < 0.01) return '< $0.01';
  return `$${usd.toFixed(2)}`;
}
