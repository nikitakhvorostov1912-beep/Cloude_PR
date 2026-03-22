import { describe, it, expect } from 'vitest';
import {
  estimateWhisperCost,
  estimateLLMCost,
  estimateTotalCost,
  estimateCostBeforeProcessing,
  formatCost,
} from '@/lib/cost-estimator';

describe('estimateWhisperCost', () => {
  it('calculates cost for 60-second audio', () => {
    // 60s = 1 min * $0.006 = $0.006
    expect(estimateWhisperCost(60)).toBeCloseTo(0.006, 6);
  });

  it('calculates cost for 0 seconds', () => {
    expect(estimateWhisperCost(0)).toBe(0);
  });

  it('calculates cost for 30 minutes', () => {
    // 1800s = 30 min * $0.006 = $0.18
    expect(estimateWhisperCost(1800)).toBeCloseTo(0.18, 4);
  });

  it('is proportional to duration', () => {
    const cost30 = estimateWhisperCost(30 * 60);
    const cost60 = estimateWhisperCost(60 * 60);
    expect(cost60).toBeCloseTo(cost30 * 2, 6);
  });
});

describe('estimateLLMCost', () => {
  const sampleText = 'Тестовый транскрипт '.repeat(100); // ~2000 chars

  it('returns positive costs for claude', () => {
    const { inputCost, outputCost } = estimateLLMCost(sampleText, 3, 'claude');
    expect(inputCost).toBeGreaterThan(0);
    expect(outputCost).toBeGreaterThan(0);
  });

  it('returns positive costs for openai', () => {
    const { inputCost, outputCost } = estimateLLMCost(sampleText, 3, 'openai');
    expect(inputCost).toBeGreaterThan(0);
    expect(outputCost).toBeGreaterThan(0);
  });

  it('scales linearly with artifact count', () => {
    const cost1 = estimateLLMCost(sampleText, 1, 'claude');
    const cost3 = estimateLLMCost(sampleText, 3, 'claude');
    expect(cost3.inputCost).toBeCloseTo(cost1.inputCost * 3, 6);
    expect(cost3.outputCost).toBeCloseTo(cost1.outputCost * 3, 6);
  });

  it('claude is more expensive than openai (input)', () => {
    const claude = estimateLLMCost(sampleText, 6, 'claude');
    const openai = estimateLLMCost(sampleText, 6, 'openai');
    expect(claude.inputCost).toBeGreaterThan(openai.inputCost);
  });
});

describe('estimateTotalCost', () => {
  it('sums whisper + llm costs', () => {
    const transcript = 'Текст встречи '.repeat(200);
    const breakdown = estimateTotalCost(3600, transcript, 6, 'claude');
    expect(breakdown.totalCost).toBeCloseTo(
      breakdown.whisperCost + breakdown.llmInputCost + breakdown.llmOutputCost,
      6,
    );
  });

  it('includes details', () => {
    const breakdown = estimateTotalCost(600, 'Короткая встреча', 2, 'openai');
    expect(breakdown.details.artifactCount).toBe(2);
    expect(breakdown.details.provider).toBe('openai');
    expect(breakdown.details.whisperMinutes).toBeCloseTo(10, 4);
  });

  it('total is positive for valid inputs', () => {
    const breakdown = estimateTotalCost(1800, 'Текст'.repeat(100), 3, 'openai');
    expect(breakdown.totalCost).toBeGreaterThan(0);
  });
});

describe('estimateCostBeforeProcessing', () => {
  it('returns positive estimate', () => {
    const cost = estimateCostBeforeProcessing(3600, 6, 'claude');
    expect(cost).toBeGreaterThan(0);
  });

  it('higher artifact count = higher cost', () => {
    const cost3 = estimateCostBeforeProcessing(1800, 3, 'openai');
    const cost6 = estimateCostBeforeProcessing(1800, 6, 'openai');
    expect(cost6).toBeGreaterThan(cost3);
  });

  it('longer audio = higher cost', () => {
    const cost30 = estimateCostBeforeProcessing(30 * 60, 3, 'claude');
    const cost60 = estimateCostBeforeProcessing(60 * 60, 3, 'claude');
    expect(cost60).toBeGreaterThan(cost30);
  });
});

describe('formatCost', () => {
  it('formats zero cost as less than penny', () => {
    expect(formatCost(0)).toBe('< $0.01');
  });

  it('formats tiny cost as less than penny', () => {
    expect(formatCost(0.001)).toBe('< $0.01');
  });

  it('formats 1 cent correctly', () => {
    expect(formatCost(0.01)).toBe('$0.01');
  });

  it('formats dollars correctly', () => {
    expect(formatCost(1.234)).toBe('$1.23');
  });

  it('formats larger amounts', () => {
    expect(formatCost(10.5)).toBe('$10.50');
  });
});
