/**
 * Абстрактный LLM-сервис: Claude, OpenAI, Gemini, Groq, DeepSeek.
 * Claude — свой формат. Остальные — OpenAI-совместимые.
 * В Tauri: вызов через Rust backend (API-ключ не виден в DevTools).
 * В dev: прямой fetch / Vite proxy.
 */

import { invoke } from '@tauri-apps/api/core';
import { trackApiUsage } from '@/lib/rate-limiter';
import { markProviderBlocked, getAvailableProviders, type ProviderSlot } from '@/lib/provider-router';
import type { LLMProvider, APIKeys } from '@/types/api.types';
import type { ArtifactType } from '@/types/artifact.types';
import type { BuiltPrompt } from '@/lib/prompts';
import { tryParseJSON } from '@/lib/validators';
import {
  AI_MODELS,
  API_ENDPOINTS,
  ANTHROPIC_VERSION,
  DEFAULT_LLM_MODELS,
  PROVIDER_BASE_URLS,
  LLM_DEV_ENDPOINTS,
  PROVIDER_NAMES,
} from '@/lib/constants';

/** Retry конфигурация */
const MAX_RETRIES = 3;
const RETRY_DELAYS = [5_000, 15_000, 30_000];

/** Таймаут для LLM API (dev fetch режим): 2 минуты */
const REQUEST_TIMEOUT_MS = 2 * 60 * 1000;

const isTauri = (): boolean => '__TAURI_INTERNALS__' in window;

export interface LLMResult {
  text: string;
  data: Record<string, unknown> | null;
  parseError: string | null;
  tokensUsed: {
    input: number;
    output: number;
    total: number;
  };
  model: string;
  provider: LLMProvider;
  artifactType: ArtifactType;
}

export interface LLMStreamCallback {
  onToken?: (token: string) => void;
  onProgress?: (message: string) => void;
}

/**
 * Генерирует один артефакт через LLM. Поддерживает retry.
 */
export async function generateArtifact(
  prompt: BuiltPrompt,
  apiKey: string,
  provider: LLMProvider,
  callbacks?: LLMStreamCallback,
  modelOverride?: string,
): Promise<LLMResult> {
  const model = modelOverride || DEFAULT_LLM_MODELS[provider];
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      if (attempt > 0) {
        const delay = RETRY_DELAYS[attempt - 1];
        callbacks?.onProgress?.(`Ошибка: ${lastError?.message}. Попытка ${attempt + 1}/${MAX_RETRIES + 1} через ${delay / 1000} сек...`);
        await sleep(delay);
      }

      callbacks?.onProgress?.(`Генерация: ${prompt.artifactType}...`);

      const result =
        provider === 'claude'
          ? await callClaude(prompt, apiKey, model, callbacks)
          : await callOpenAICompatible(prompt, apiKey, model, provider, callbacks);

      trackApiUsage(provider, result.tokensUsed.total);
      return result;
    } catch (error) {
      if (error instanceof LLMError && (
        error.code === 'INVALID_KEY' ||
        error.code === 'INSUFFICIENT_FUNDS' ||
        error.code === 'REQUEST_TOO_LARGE' ||
        error.code === 'PROVIDER_BLOCKED' ||
        error.code === 'MODEL_NOT_FOUND'
      )) {
        throw error;
      }
      lastError = error instanceof Error ? error : new Error(String(error));
      console.error(`[LLM] Attempt ${attempt + 1} failed:`, lastError.message);
      callbacks?.onProgress?.(`Ошибка: ${lastError.message}`);
    }
  }

  throw new LLMError(
    `Генерация артефакта «${prompt.artifactType}» не удалась после ${MAX_RETRIES} попыток: ${lastError?.message}`,
    'MAX_RETRIES_EXCEEDED',
  );
}

/**
 * Генерирует несколько артефактов с параллелизацией (fan-out).
 * EC-10: каждый промпт независим — partial results.
 *
 * @param providerSlots — если задан, каждый артефакт получает свой провайдер (fan-out).
 *                        Если null — все идут через один provider.
 */
export async function generateArtifacts(
  prompts: BuiltPrompt[],
  apiKey: string,
  provider: LLMProvider,
  callbacks?: {
    onArtifactStart?: (type: ArtifactType) => void;
    onArtifactComplete?: (type: ArtifactType, result: LLMResult) => void;
    onArtifactError?: (type: ArtifactType, error: Error) => void;
    onToken?: (type: ArtifactType, token: string) => void;
    onProgress?: (message: string) => void;
  },
  modelOverride?: string,
  providerSlots?: ProviderSlot[],
  fallbackApiKeys?: APIKeys,
): Promise<Map<ArtifactType, LLMResult | Error>> {
  const results = new Map<ArtifactType, LLMResult | Error>();

  // Определяем concurrency: если fan-out — до 4 параллельных, иначе 1
  const concurrency = providerSlots && providerSlots.length > 1
    ? Math.min(4, providerSlots.length)
    : 1;

  /** Коды ошибок, при которых провайдер блокируется и нужен fallback */
  const BLOCKING_CODES = new Set([
    'RATE_LIMIT', 'REQUEST_TOO_LARGE', 'PROVIDER_BLOCKED',
    'MODEL_NOT_FOUND', 'INSUFFICIENT_FUNDS',
  ]);

  const queue = prompts.map((prompt, i) => ({
    prompt,
    slot: providerSlots?.[i] ?? null,
  }));
  const running: Promise<void>[] = [];

  const processOne = async (item: { prompt: BuiltPrompt; slot: ProviderSlot | null }) => {
    const { prompt, slot } = item;
    let effectiveProvider = slot?.provider ?? provider;
    let effectiveKey = slot?.apiKey ?? apiKey;
    let effectiveModel = modelOverride || slot?.model || DEFAULT_LLM_MODELS[effectiveProvider];
    const triedProviders = new Set<LLMProvider>();

    callbacks?.onArtifactStart?.(prompt.artifactType);

    while (true) {
      try {
        const result = await generateArtifact(prompt, effectiveKey, effectiveProvider, {
          onToken: (token) => callbacks?.onToken?.(prompt.artifactType, token),
          onProgress: callbacks?.onProgress,
        }, effectiveModel);
        results.set(prompt.artifactType, result);
        callbacks?.onArtifactComplete?.(prompt.artifactType, result);
        return;
      } catch (error) {
        triedProviders.add(effectiveProvider);

        // Помечаем провайдер как заблокированный при блокирующей ошибке
        const isBlocking = error instanceof LLMError && BLOCKING_CODES.has(error.code);
        if (isBlocking) {
          markProviderBlocked(effectiveProvider);
          callbacks?.onProgress?.(`⚠ ${PROVIDER_NAMES[effectiveProvider]}: ${(error as LLMError).message}`);

          // Ищем fallback-провайдер, которого ещё не пробовали
          if (fallbackApiKeys) {
            const available = getAvailableProviders(fallbackApiKeys);
            const fallback = available.find((s) => !triedProviders.has(s.provider));
            if (fallback) {
              callbacks?.onProgress?.(`↻ Переключение на ${PROVIDER_NAMES[fallback.provider]}...`);
              effectiveProvider = fallback.provider;
              effectiveKey = fallback.apiKey;
              effectiveModel = modelOverride || fallback.model;
              continue; // Retry with next provider
            }
          }
        }

        // Нет fallback или ошибка не блокирующая — записываем ошибку
        const err = error instanceof Error ? error : new Error(String(error));
        results.set(prompt.artifactType, err);
        callbacks?.onArtifactError?.(prompt.artifactType, err);
        return;
      }
    }
  };

  while (queue.length > 0 || running.length > 0) {
    while (running.length < concurrency && queue.length > 0) {
      const item = queue.shift()!;
      const task = processOne(item);
      running.push(task);
      task.then(() => {
        const idx = running.indexOf(task);
        if (idx >= 0) running.splice(idx, 1);
      });
    }
    if (running.length > 0) await Promise.race(running);
  }

  return results;
}

// ─── OpenAI-Compatible Providers (OpenAI, Gemini, Groq, DeepSeek) ───────────

/**
 * Универсальный вызов к OpenAI-совместимому API.
 * Работает для: openai, gemini, groq, deepseek, mimo.
 * MiMo использует нестандартный заголовок `api-key` вместо `Authorization: Bearer`.
 */
async function callOpenAICompatible(
  prompt: BuiltPrompt,
  apiKey: string,
  model: string,
  provider: LLMProvider,
  callbacks?: LLMStreamCallback,
): Promise<LLMResult> {
  const body = {
    model,
    messages: [
      { role: 'system', content: prompt.system },
      { role: 'user', content: prompt.user },
    ],
    temperature: prompt.temperature,
    max_tokens: prompt.maxTokens,
    response_format: { type: 'json_object' },
  };

  let data: Record<string, unknown>;

  // MiMo использует нестандартный заголовок api-key вместо Authorization: Bearer
  const authHeaderName = provider === 'mimo' ? 'api-key' : undefined;

  if (isTauri()) {
    const endpointUrl = `${PROVIDER_BASE_URLS[provider]}/chat/completions`;
    const responseJson = await invoke<string>('call_openai_compatible_api', {
      endpointUrl,
      body: JSON.stringify(body),
      apiKey,
      authHeaderName: authHeaderName || null,
    }).catch((err: string): never => {
      parseAndThrowApiError(err, provider);
    });
    data = JSON.parse(responseJson) as Record<string, unknown>;
  } else {
    const devEndpoint = LLM_DEV_ENDPOINTS[provider];
    const authHeaders: Record<string, string> = provider === 'mimo'
      ? { 'api-key': apiKey }
      : { Authorization: `Bearer ${apiKey}` };
    const response = await fetchWithTimeout(devEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      console.error(`[LLM] ${provider} API ${response.status}:`, errorText.slice(0, 300));
      handleAPIError(response.status, errorText, provider);
    }
    data = await response.json() as Record<string, unknown>;
  }

  const text = (data.choices as Array<Record<string, Record<string, unknown>>>)?.[0]?.message?.content as string || '';
  const usage = (data.usage as Record<string, number>) || {};

  callbacks?.onToken?.(text);

  return parseAndBuildResult(
    text,
    { inputTokens: usage.prompt_tokens || 0, outputTokens: usage.completion_tokens || 0 },
    model,
    provider,
    prompt.artifactType,
  );
}

// ─── Anthropic Claude (свой формат) ─────────────────────────────────────────

async function callClaude(
  prompt: BuiltPrompt,
  apiKey: string,
  model: string,
  callbacks?: LLMStreamCallback,
): Promise<LLMResult> {
  const body = {
    model,
    max_tokens: prompt.maxTokens,
    system: prompt.system,
    messages: [{ role: 'user', content: prompt.user }],
    temperature: prompt.temperature,
  };

  let data: Record<string, unknown>;

  if (isTauri()) {
    const responseJson = await invoke<string>('call_claude_api', {
      body: JSON.stringify(body),
      apiKey,
    }).catch((err: string): never => {
      parseAndThrowApiError(err, 'claude');
    });
    data = JSON.parse(responseJson) as Record<string, unknown>;
  } else {
    const response = await fetchWithTimeout(API_ENDPOINTS.anthropicMessages, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': ANTHROPIC_VERSION,
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      console.error(`[LLM] Claude API ${response.status}:`, errorText.slice(0, 300));
      handleAPIError(response.status, errorText, 'claude');
    }
    data = await response.json() as Record<string, unknown>;
  }

  const text =
    (data.content as Array<Record<string, unknown>>)?.[0]?.text as string || '';
  const usage = (data.usage as Record<string, number>) || {};

  callbacks?.onToken?.(text);

  return parseAndBuildResult(
    text,
    { inputTokens: usage.input_tokens || 0, outputTokens: usage.output_tokens || 0 },
    model,
    'claude',
    prompt.artifactType,
  );
}

// ─── Общие утилиты ──────────────────────────────────────────────────────────

function parseAndBuildResult(
  text: string,
  tokens: { inputTokens: number; outputTokens: number },
  model: string,
  provider: LLMProvider,
  artifactType: ArtifactType,
): LLMResult {
  const parsed = tryParseJSON(text);
  return {
    text,
    data: parsed.ok ? (parsed.data as Record<string, unknown>) : null,
    parseError: parsed.ok ? null : (parsed as { error: string }).error,
    tokensUsed: {
      input: tokens.inputTokens,
      output: tokens.outputTokens,
      total: tokens.inputTokens + tokens.outputTokens,
    },
    model,
    provider,
    artifactType,
  };
}

/** Разбирает строку ошибки из Rust backend и бросает LLMError. */
function parseAndThrowApiError(err: string, provider: LLMProvider): never {
  console.error(`[LLM] Tauri ${provider} error:`, err);
  // Формат Rust ошибок: "{PREFIX}:{status}:{body}"
  const prefixes = ['CLAUDE_API_ERROR', 'OPENAI_API_ERROR'];
  for (const prefix of prefixes) {
    if (err.startsWith(prefix)) {
      const firstColon = err.indexOf(':');
      const secondColon = err.indexOf(':', firstColon + 1);
      const statusStr = err.slice(firstColon + 1, secondColon);
      const bodyStr = err.slice(secondColon + 1);
      handleAPIError(parseInt(statusStr, 10), bodyStr, provider);
    }
  }
  throw new LLMError(`Ошибка Tauri: ${err}`, 'API_ERROR');
}

/** Обработка HTTP-ошибок API. */
function handleAPIError(status: number, body: string, provider: LLMProvider): never {
  const name = PROVIDER_NAMES[provider] || provider;
  if (status === 401) throw new LLMError(`Невалидный API-ключ ${name}.`, 'INVALID_KEY');
  if (status === 429) throw new LLMError(`Превышен лимит запросов ${name}. Повторная попытка...`, 'RATE_LIMIT');
  if (status === 402 || body.includes('insufficient') || body.includes('credit balance')) {
    throw new LLMError(`Недостаточно средств на аккаунте ${name}. Пополните баланс.`, 'INSUFFICIENT_FUNDS');
  }
  // 413: запрос слишком большой для провайдера (например, Groq 6K TPM vs 46K транскрипт)
  if (status === 413 || body.includes('Request too large') || body.includes('token limit')) {
    throw new LLMError(`Запрос слишком большой для ${name}. Переключение на другой провайдер.`, 'REQUEST_TOO_LARGE');
  }
  // 403: доступ запрещён / ключ приостановлен / аккаунт заблокирован
  if (status === 403 || body.includes('suspended') || body.includes('blocked') || body.includes('forbidden')) {
    throw new LLMError(`Доступ запрещён ${name} (ключ приостановлен или аккаунт заблокирован).`, 'PROVIDER_BLOCKED');
  }
  // 404: модель не найдена / endpoint не существует
  if (status === 404 || body.includes('model_not_found') || body.includes('does not exist')) {
    throw new LLMError(`Модель не найдена у ${name}. Проверьте настройки.`, 'MODEL_NOT_FOUND');
  }
  if (status >= 500) throw new LLMError(`Ошибка сервера ${name} (${status}).`, 'SERVER_ERROR');
  throw new LLMError(`Ошибка ${name} API: ${status} — ${body.slice(0, 200)}`, 'API_ERROR');
}

// ─── Валидация ключей ───────────────────────────────────────────────────────

/** Проверяет валидность API-ключа Claude. */
export async function validateClaudeKey(
  apiKey: string,
): Promise<{ valid: boolean; error?: string }> {
  try {
    if (isTauri()) {
      const valid = await invoke<boolean>('validate_claude_key', { apiKey });
      return valid ? { valid: true } : { valid: false, error: 'Невалидный API-ключ' };
    }
    const response = await fetch(API_ENDPOINTS.anthropicMessages, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': ANTHROPIC_VERSION,
      },
      body: JSON.stringify({
        model: AI_MODELS.claudeLight,
        max_tokens: 10,
        messages: [{ role: 'user', content: 'test' }],
      }),
    });
    if (response.ok) return { valid: true };
    if (response.status === 401) return { valid: false, error: 'Невалидный API-ключ' };
    if (response.status === 402) return { valid: false, error: 'Недостаточно средств' };
    return { valid: false, error: `Ошибка проверки: ${response.status}` };
  } catch {
    return { valid: false, error: 'Нет подключения к API' };
  }
}

/** Проверяет валидность ключа OpenAI-совместимого провайдера (Groq, Gemini, DeepSeek, OpenAI). */
export async function validateOpenAICompatibleKey(
  apiKey: string,
  provider: Exclude<LLMProvider, 'claude'>,
): Promise<{ valid: boolean; error?: string }> {
  try {
    const modelsUrl = `${PROVIDER_BASE_URLS[provider]}/models`;
    if (isTauri()) {
      const valid = await invoke<boolean>('validate_api_key_generic', {
        validationUrl: modelsUrl,
        apiKey,
      });
      return valid ? { valid: true } : { valid: false, error: 'Невалидный API-ключ' };
    }
    // Dev: простой completion-тест
    const devEndpoint = LLM_DEV_ENDPOINTS[provider];
    const valAuthHeaders: Record<string, string> = provider === 'mimo'
      ? { 'api-key': apiKey }
      : { Authorization: `Bearer ${apiKey}` };
    const response = await fetch(devEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...valAuthHeaders,
      },
      body: JSON.stringify({
        model: DEFAULT_LLM_MODELS[provider],
        max_tokens: 5,
        messages: [{ role: 'user', content: 'test' }],
      }),
    });
    if (response.ok) return { valid: true };
    if (response.status === 401) return { valid: false, error: 'Невалидный API-ключ' };
    return { valid: false, error: `Ошибка проверки: ${response.status}` };
  } catch {
    return { valid: false, error: 'Нет подключения к API' };
  }
}

export class LLMError extends Error {
  constructor(
    message: string,
    public code:
      | 'INVALID_KEY'
      | 'RATE_LIMIT'
      | 'INSUFFICIENT_FUNDS'
      | 'REQUEST_TOO_LARGE'
      | 'PROVIDER_BLOCKED'
      | 'MODEL_NOT_FOUND'
      | 'SERVER_ERROR'
      | 'API_ERROR'
      | 'MAX_RETRIES_EXCEEDED',
  ) {
    super(message);
    this.name = 'LLMError';
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new LLMError('Превышено время ожидания ответа от LLM API (2 мин).', 'API_ERROR');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}
