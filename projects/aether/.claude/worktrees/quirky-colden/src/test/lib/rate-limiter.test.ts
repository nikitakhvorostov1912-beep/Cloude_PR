import { describe, it, expect, beforeEach } from 'vitest';
import { trackApiUsage, checkRateLimitWarnings, getDailyUsageSummary } from '@/lib/rate-limiter';

describe('rate-limiter', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('trackApiUsage', () => {
    it('tracks openai token usage', () => {
      trackApiUsage('openai', 1000);
      const summary = getDailyUsageSummary();
      expect(summary.openaiTokens).toBe(1000);
    });

    it('tracks claude (anthropic) token usage', () => {
      trackApiUsage('claude', 500);
      const summary = getDailyUsageSummary();
      expect(summary.anthropicTokens).toBe(500);
    });

    it('accumulates multiple openai calls', () => {
      trackApiUsage('openai', 100);
      trackApiUsage('openai', 200);
      trackApiUsage('openai', 300);
      expect(getDailyUsageSummary().openaiTokens).toBe(600);
    });

    it('accumulates multiple claude calls', () => {
      trackApiUsage('claude', 100);
      trackApiUsage('claude', 400);
      expect(getDailyUsageSummary().anthropicTokens).toBe(500);
    });

    it('increments request count for each call', () => {
      trackApiUsage('openai', 100);
      trackApiUsage('claude', 100);
      expect(getDailyUsageSummary().requestCount).toBe(2);
    });
  });

  describe('checkRateLimitWarnings', () => {
    it('returns empty array at 0 usage', () => {
      expect(checkRateLimitWarnings()).toEqual([]);
    });

    it('returns no warning below 80% OpenAI', () => {
      trackApiUsage('openai', 300_000); // 60% of 500K
      expect(checkRateLimitWarnings()).toHaveLength(0);
    });

    it('returns warning when OpenAI usage >= 80%', () => {
      trackApiUsage('openai', 410_000); // 82% of 500K
      const warnings = checkRateLimitWarnings();
      expect(warnings).toHaveLength(1);
      expect(warnings[0]).toContain('OpenAI');
    });

    it('returns warning when Claude usage >= 80%', () => {
      trackApiUsage('claude', 170_000); // 85% of 200K
      const warnings = checkRateLimitWarnings();
      expect(warnings).toHaveLength(1);
      expect(warnings[0]).toContain('Claude');
    });

    it('returns multiple warnings when both exceed threshold', () => {
      trackApiUsage('openai', 450_000);
      trackApiUsage('claude', 180_000);
      const warnings = checkRateLimitWarnings();
      expect(warnings.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('getDailyUsageSummary', () => {
    it('starts with zero counts', () => {
      const summary = getDailyUsageSummary();
      expect(summary.openaiTokens).toBe(0);
      expect(summary.anthropicTokens).toBe(0);
      expect(summary.requestCount).toBe(0);
    });

    it('returns percentage fields', () => {
      const summary = getDailyUsageSummary();
      expect(summary).toHaveProperty('openaiPct');
      expect(summary).toHaveProperty('anthropicPct');
    });

    it('calculates correct percentages', () => {
      trackApiUsage('openai', 250_000); // 50% of 500K
      const summary = getDailyUsageSummary();
      expect(summary.openaiPct).toBe(50);
    });

    it('caps percentage calculation correctly', () => {
      trackApiUsage('claude', 200_000); // 100% of 200K
      const summary = getDailyUsageSummary();
      expect(summary.anthropicPct).toBe(100);
    });
  });
});
