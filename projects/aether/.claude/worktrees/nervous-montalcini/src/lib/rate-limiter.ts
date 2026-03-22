/**
 * Простой rate limiter для отслеживания использования API.
 * Хранит счётчики в памяти (сбрасываются при перезапуске).
 * Предупреждает пользователя при приближении к дневному лимиту.
 */

interface DailyUsage {
  date: string; // YYYY-MM-DD
  openaiTokens: number;
  anthropicTokens: number;
  requestCount: number;
}

// Мягкие лимиты — предупреждение (не блокировка)
const SOFT_LIMITS = {
  openaiTokensPerDay: 500_000,   // ~$5 для gpt-4o
  anthropicTokensPerDay: 200_000, // ~$3 для claude-sonnet
  requestsPerDay: 500,
};

function getTodayKey(): string {
  return new Date().toISOString().slice(0, 10);
}

function loadUsage(): DailyUsage {
  try {
    const raw = localStorage.getItem('aether-daily-usage');
    if (!raw) return { date: getTodayKey(), openaiTokens: 0, anthropicTokens: 0, requestCount: 0 };
    const usage = JSON.parse(raw) as DailyUsage;
    // Сброс если новый день
    if (usage.date !== getTodayKey()) {
      return { date: getTodayKey(), openaiTokens: 0, anthropicTokens: 0, requestCount: 0 };
    }
    return usage;
  } catch {
    return { date: getTodayKey(), openaiTokens: 0, anthropicTokens: 0, requestCount: 0 };
  }
}

function saveUsage(usage: DailyUsage): void {
  try {
    localStorage.setItem('aether-daily-usage', JSON.stringify(usage));
  } catch {
    // Не критично
  }
}

/** Обновляет счётчик использования после запроса. */
export function trackApiUsage(
  provider: 'openai' | 'claude',
  tokensUsed: number,
): void {
  const usage = loadUsage();
  usage.requestCount += 1;
  if (provider === 'openai') {
    usage.openaiTokens += tokensUsed;
  } else {
    usage.anthropicTokens += tokensUsed;
  }
  saveUsage(usage);
}

/** Возвращает предупреждения если приближаемся к лимитам. */
export function checkRateLimitWarnings(): string[] {
  const usage = loadUsage();
  const warnings: string[] = [];

  const openaiPct = (usage.openaiTokens / SOFT_LIMITS.openaiTokensPerDay) * 100;
  const anthropicPct = (usage.anthropicTokens / SOFT_LIMITS.anthropicTokensPerDay) * 100;
  const reqPct = (usage.requestCount / SOFT_LIMITS.requestsPerDay) * 100;

  if (openaiPct >= 80) {
    warnings.push(
      `OpenAI: использовано ${openaiPct.toFixed(0)}% дневного лимита токенов (${usage.openaiTokens.toLocaleString()})`,
    );
  }
  if (anthropicPct >= 80) {
    warnings.push(
      `Claude: использовано ${anthropicPct.toFixed(0)}% дневного лимита токенов (${usage.anthropicTokens.toLocaleString()})`,
    );
  }
  if (reqPct >= 80) {
    warnings.push(
      `Запросы: использовано ${reqPct.toFixed(0)}% дневного лимита (${usage.requestCount})`,
    );
  }

  return warnings;
}

/** Возвращает текущую статистику использования за сегодня. */
export function getDailyUsageSummary(): {
  openaiTokens: number;
  anthropicTokens: number;
  requestCount: number;
  openaiPct: number;
  anthropicPct: number;
} {
  const usage = loadUsage();
  return {
    openaiTokens: usage.openaiTokens,
    anthropicTokens: usage.anthropicTokens,
    requestCount: usage.requestCount,
    openaiPct: Math.round((usage.openaiTokens / SOFT_LIMITS.openaiTokensPerDay) * 100),
    anthropicPct: Math.round((usage.anthropicTokens / SOFT_LIMITS.anthropicTokensPerDay) * 100),
  };
}
