/**
 * ProviderRouter — интеллектуальная маршрутизация запросов по LLM-провайдерам.
 *
 * Режим 'auto':
 *   - Распределяет артефакты по доступным провайдерам (fan-out)
 *   - При rate limit (429) автоматически переключается на следующий провайдер
 *   - Приоритет: бесплатные → дешёвые → платные
 *
 * Режим 'single':
 *   - Использует один выбранный провайдер
 *   - При rate limit — fallback на следующий доступный
 */

import type { LLMProvider, APIKeys } from '@/types/api.types';
import { isProviderExhausted } from './rate-limiter';
import { DEFAULT_LLM_MODELS } from './constants';

/** Приоритет провайдеров: бесплатные с наибольшим лимитом первыми */
const PROVIDER_PRIORITY: LLMProvider[] = [
  'groq',       // 500K/день, быстрый
  'gemini',     // 250 RPD, мощный
  'cerebras',   // 1M/день, сверхбыстрый
  'mistral',    // 33M/месяц
  'deepseek',   // 5M бонус
  'openrouter', // 29 бесплатных моделей
  'mimo',       // $0.09/M
  'openai',     // платный
  'claude',     // платный
];

/** Маппинг LLM-провайдер → поле APIKeys */
export const LLM_KEY_MAP: Record<LLMProvider, keyof APIKeys> = {
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

export interface ProviderSlot {
  provider: LLMProvider;
  model: string;
  apiKey: string;
}

/** Провайдеры, заблокированные rate limit в текущей сессии (сбрасываются при перезапуске) */
const blockedProviders = new Set<LLMProvider>();

/** Пометить провайдер как заблокированный (после 429). */
export function markProviderBlocked(provider: LLMProvider): void {
  blockedProviders.add(provider);
}

/** Снять блокировку (например, при новом запуске пайплайна). */
export function resetBlockedProviders(): void {
  blockedProviders.clear();
}

/**
 * Возвращает список доступных провайдеров, отсортированных по приоритету.
 * Фильтрует: без ключа, исчерпанные, заблокированные.
 */
export function getAvailableProviders(apiKeys: APIKeys): ProviderSlot[] {
  return PROVIDER_PRIORITY
    .filter((provider) => {
      const keyField = LLM_KEY_MAP[provider];
      const key = apiKeys[keyField];
      if (!key) return false;
      if (blockedProviders.has(provider)) return false;
      if (isProviderExhausted(provider)) return false;
      return true;
    })
    .map((provider) => ({
      provider,
      model: DEFAULT_LLM_MODELS[provider],
      apiKey: apiKeys[LLM_KEY_MAP[provider]],
    }));
}

/**
 * Возвращает fallback chain начиная с предпочтительного провайдера.
 * Если preferred недоступен — начинает с первого доступного.
 */
export function buildFallbackChain(
  preferred: LLMProvider,
  apiKeys: APIKeys,
): ProviderSlot[] {
  const available = getAvailableProviders(apiKeys);
  if (available.length === 0) return [];

  // Ставим preferred первым, если он доступен
  const preferredIdx = available.findIndex((s) => s.provider === preferred);
  if (preferredIdx > 0) {
    const [pref] = available.splice(preferredIdx, 1);
    available.unshift(pref);
  }

  return available;
}

/**
 * Распределяет N артефактов по доступным провайдерам (round-robin).
 * Каждый артефакт получает свой провайдер для параллельной генерации.
 */
export function distributeAcrossProviders(
  count: number,
  apiKeys: APIKeys,
  preferred: LLMProvider,
): ProviderSlot[] {
  const available = buildFallbackChain(preferred, apiKeys);
  if (available.length === 0) return [];

  const assignments: ProviderSlot[] = [];
  for (let i = 0; i < count; i++) {
    assignments.push(available[i % available.length]);
  }
  return assignments;
}

