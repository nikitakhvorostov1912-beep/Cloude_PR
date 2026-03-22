/**
 * Оценка стоимости API-вызовов.
 * Цены актуальны на март 2026.
 */

import type { LLMProvider, STTProvider } from '@/types/api.types';
import { estimateTokens } from './chunking';

/** Цены STT по провайдеру (за минуту) */
const STT_PRICES: Record<STTProvider, number> = {
  openai: 0.006,
  groq: 0,
  gemini: 0,
};

/** Цены LLM по провайдеру (за 1 токен) */
const LLM_PRICES: Record<LLMProvider, { input: number; output: number }> = {
  claude:   { input: 3.0 / 1_000_000,  output: 15.0 / 1_000_000 },
  openai:   { input: 2.50 / 1_000_000, output: 10.0 / 1_000_000 },
  gemini:   { input: 0, output: 0 },     // бесплатно (250 RPD)
  groq:     { input: 0, output: 0 },     // бесплатно (500K TPD)
  deepseek: { input: 0.14 / 1_000_000, output: 0.28 / 1_000_000 },
  mimo:     { input: 0.09 / 1_000_000, output: 0.09 / 1_000_000 },
  cerebras: { input: 0, output: 0 },       // бесплатно (1M TPD)
  mistral:  { input: 0, output: 0 },       // бесплатно (33M TPD)
  openrouter: { input: 0, output: 0 },     // бесплатно (29 моделей)
};

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
export function estimateWhisperCost(durationSeconds: number, sttProvider: STTProvider = 'groq'): number {
  const minutes = durationSeconds / 60;
  return minutes * STT_PRICES[sttProvider];
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

  const prices = LLM_PRICES[provider] || LLM_PRICES.openai;

  return {
    inputCost: totalInputTokens * prices.input,
    outputCost: totalOutputTokens * prices.output,
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

  const prices = LLM_PRICES[provider] || LLM_PRICES.openai;
  const inputPrice = prices.input;
  const outputPrice = prices.output;

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
