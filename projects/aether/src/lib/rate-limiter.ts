/**
 * Rate limiter для отслеживания использования API.
 * Хранит счётчики в памяти (сбрасываются при перезапуске).
 * Предупреждает пользователя при приближении к дневному лимиту.
 */

import type { LLMProvider } from '@/types/api.types';
import { PROVIDER_NAMES } from '@/lib/constants';

interface ProviderUsage {
  tokens: number;
  requests: number;
}

interface DailyUsage {
  date: string; // YYYY-MM-DD
  providers: Record<string, ProviderUsage>;
}

/** Мягкие лимиты — предупреждение (не блокировка) */
const SOFT_LIMITS: Record<string, { tokensPerDay: number; requestsPerDay: number }> = {
  gemini:     { tokensPerDay: 250_000,    requestsPerDay: 250 },
  groq:       { tokensPerDay: 500_000,    requestsPerDay: 14_400 },
  deepseek:   { tokensPerDay: 5_000_000,  requestsPerDay: 1_000 },
  openai:     { tokensPerDay: 500_000,    requestsPerDay: 500 },
  claude:     { tokensPerDay: 200_000,    requestsPerDay: 500 },
  mimo:       { tokensPerDay: 1_000_000,  requestsPerDay: 1_000 },
  cerebras:   { tokensPerDay: 1_000_000,  requestsPerDay: 1_800 },
  mistral:    { tokensPerDay: 33_000_000, requestsPerDay: 1_000 },
  openrouter: { tokensPerDay: 1_000_000,  requestsPerDay: 1_000 },
};

const WARN_THRESHOLD_PCT = 80;

function getTodayKey(): string {
  return new Date().toISOString().slice(0, 10);
}

function emptyProviderUsage(): ProviderUsage {
  return { tokens: 0, requests: 0 };
}

function loadUsage(): DailyUsage {
  try {
    const raw = localStorage.getItem('aether-daily-usage-v2');
    if (!raw) return { date: getTodayKey(), providers: {} };
    const usage = JSON.parse(raw) as DailyUsage;
    if (usage.date !== getTodayKey()) {
      return { date: getTodayKey(), providers: {} };
    }
    return usage;
  } catch {
    return { date: getTodayKey(), providers: {} };
  }
}

function saveUsage(usage: DailyUsage): void {
  try {
    localStorage.setItem('aether-daily-usage-v2', JSON.stringify(usage));
  } catch {
    // Не критично
  }
}

/** Обновляет счётчик использования после запроса. */
export function trackApiUsage(
  provider: LLMProvider | string,
  tokensUsed: number,
): void {
  const usage = loadUsage();
  if (!usage.providers[provider]) {
    usage.providers[provider] = emptyProviderUsage();
  }
  usage.providers[provider].tokens += tokensUsed;
  usage.providers[provider].requests += 1;
  saveUsage(usage);
}

/** Возвращает предупреждения если приближаемся к лимитам. */
export function checkRateLimitWarnings(): string[] {
  const usage = loadUsage();
  const warnings: string[] = [];

  for (const [provider, limits] of Object.entries(SOFT_LIMITS)) {
    const pu = usage.providers[provider];
    if (!pu) continue;

    const name = PROVIDER_NAMES[provider as LLMProvider] || provider;

    const tokenPct = (pu.tokens / limits.tokensPerDay) * 100;
    if (tokenPct >= WARN_THRESHOLD_PCT) {
      warnings.push(
        `${name}: использовано ${tokenPct.toFixed(0)}% дневного лимита токенов (${pu.tokens.toLocaleString()}/${limits.tokensPerDay.toLocaleString()})`,
      );
    }

    const reqPct = (pu.requests / limits.requestsPerDay) * 100;
    if (reqPct >= WARN_THRESHOLD_PCT) {
      warnings.push(
        `${name}: использовано ${reqPct.toFixed(0)}% дневного лимита запросов (${pu.requests}/${limits.requestsPerDay})`,
      );
    }
  }

  return warnings;
}

/** Возвращает текущую статистику по провайдеру за сегодня. */
export function getProviderUsage(provider: string): ProviderUsage {
  const usage = loadUsage();
  return usage.providers[provider] || emptyProviderUsage();
}

/** Возвращает общий счётчик запросов за сегодня. */
export function getDailyRequestCount(): number {
  const usage = loadUsage();
  return Object.values(usage.providers).reduce((sum, pu) => sum + pu.requests, 0);
}

/** Проверяет, исчерпан ли лимит провайдера (>= 95% токенов или запросов). */
export function isProviderExhausted(provider: string): boolean {
  const limits = SOFT_LIMITS[provider];
  if (!limits) return false;
  const pu = getProviderUsage(provider);
  const tokenPct = (pu.tokens / limits.tokensPerDay) * 100;
  const reqPct = (pu.requests / limits.requestsPerDay) * 100;
  return tokenPct >= 95 || reqPct >= 95;
}

/** Возвращает оставшийся процент лимита для провайдера (0-100). */
export function getProviderRemainingPct(provider: string): number {
  const limits = SOFT_LIMITS[provider];
  if (!limits) return 100;
  const pu = getProviderUsage(provider);
  const tokenPct = (pu.tokens / limits.tokensPerDay) * 100;
  const reqPct = (pu.requests / limits.requestsPerDay) * 100;
  return Math.max(0, 100 - Math.max(tokenPct, reqPct));
}
