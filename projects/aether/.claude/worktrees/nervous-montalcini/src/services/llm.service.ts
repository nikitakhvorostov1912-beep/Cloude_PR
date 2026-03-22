/**
 * Абстрактный LLM-сервис для Claude и OpenAI.
 * В Tauri: вызов через Rust backend (API-ключ не виден в DevTools).
 * В dev: прямой fetch / Vite proxy.
 * Обрабатывает edge cases: EC-09 (API ошибка), EC-11 (невалидный JSON).
 */

import { invoke } from '@tauri-apps/api/core';
import { trackApiUsage } from '@/lib/rate-limiter';
import type { LLMProvider } from '@/types/api.types';
import type { ArtifactType } from '@/types/artifact.types';
import type { BuiltPrompt } from '@/lib/prompts';
import { tryParseJSON } from '@/lib/validators';

const OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions';

/** Retry конфигурация */
const MAX_RETRIES = 3;
const RETRY_DELAYS = [5_000, 15_000, 30_000];

/** Таймаут для LLM API (dev fetch режим): 2 минуты */
const REQUEST_TIMEOUT_MS = 2 * 60 * 1000;

const isTauri = (): boolean => '__TAURI_INTERNALS__' in window;

/** Модели по умолчанию */
const DEFAULT_MODELS: Record<LLMProvider, string> = {
  claude: 'claude-sonnet-4-6',
  openai: 'gpt-4o',
};

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
 * Генерирует один артефакт через LLM.
 * Поддерживает retry.
 */
export async function generateArtifact(
  prompt: BuiltPrompt,
  apiKey: string,
  provider: LLMProvider,
  callbacks?: LLMStreamCallback,
): Promise<LLMResult> {
  const model = DEFAULT_MODELS[provider];
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      if (attempt > 0) {
        const delay = RETRY_DELAYS[attempt - 1];
        callbacks?.onProgress?.(`Повторная попытка через ${delay / 1000} сек...`);
        await sleep(delay);
      }

      callbacks?.onProgress?.(`Генерация: ${prompt.artifactType}...`);

      const result =
        provider === 'openai'
          ? await callOpenAI(prompt, apiKey, model, callbacks)
          : await callClaude(prompt, apiKey, model, callbacks);

      trackApiUsage(provider, result.tokensUsed.total);
      return result;
    } catch (error) {
      if (error instanceof LLMError && error.code === 'INVALID_KEY') {
        throw error;
      }
      lastError = error instanceof Error ? error : new Error(String(error));
      callbacks?.onProgress?.(`Ошибка: ${lastError.message}`);
    }
  }

  throw new LLMError(
    `Генерация артефакта «${prompt.artifactType}» не удалась после ${MAX_RETRIES} попыток: ${lastError?.message}`,
    'MAX_RETRIES_EXCEEDED',
  );
}

/**
 * Генерирует несколько артефактов параллельно (до 3 одновременно).
 * EC-10: каждый промпт независим — partial results.
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
): Promise<Map<ArtifactType, LLMResult | Error>> {
  const results = new Map<ArtifactType, LLMResult | Error>();
  const concurrency = 3;
  const queue = [...prompts];
  const running: Promise<void>[] = [];

  const processOne = async (prompt: BuiltPrompt) => {
    callbacks?.onArtifactStart?.(prompt.artifactType);
    try {
      const result = await generateArtifact(prompt, apiKey, provider, {
        onToken: (token) => callbacks?.onToken?.(prompt.artifactType, token),
        onProgress: callbacks?.onProgress,
      });
      results.set(prompt.artifactType, result);
      callbacks?.onArtifactComplete?.(prompt.artifactType, result);
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      results.set(prompt.artifactType, err);
      callbacks?.onArtifactError?.(prompt.artifactType, err);
    }
  };

  while (queue.length > 0 || running.length > 0) {
    while (running.length < concurrency && queue.length > 0) {
      const prompt = queue.shift()!;
      const task = processOne(prompt);
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

/**
 * OpenAI Chat Completions.
 * В Tauri — через Rust invoke. В dev — прямой fetch.
 */
async function callOpenAI(
  prompt: BuiltPrompt,
  apiKey: string,
  model: string,
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

  if (isTauri()) {
    const responseJson = await invoke<string>('call_openai_api', {
      body: JSON.stringify(body),
      apiKey,
    }).catch((err: string) => {
      parseAndThrowApiError(err, 'openai');
    }) as string;
    data = JSON.parse(responseJson) as Record<string, unknown>;
  } else {
    const response = await fetchWithTimeout(OPENAI_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      handleAPIError(response.status, errorText, 'openai');
    }
    data = await response.json() as Record<string, unknown>;
  }

  const text = (data.choices as Array<Record<string, unknown>>)?.[0]?.message
    ? ((data.choices as Array<Record<string, Record<string, unknown>>>)[0].message.content as string) || ''
    : '';
  const usage = (data.usage as Record<string, number>) || {};

  callbacks?.onToken?.(text);

  return parseAndBuildResult(
    text,
    { inputTokens: usage.prompt_tokens || 0, outputTokens: usage.completion_tokens || 0 },
    model,
    'openai',
    prompt.artifactType,
  );
}

/**
 * Anthropic Claude Messages API.
 * В Tauri — через Rust invoke. В dev — через Vite proxy.
 */
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
    }).catch((err: string) => {
      parseAndThrowApiError(err, 'claude');
    }) as string;
    data = JSON.parse(responseJson) as Record<string, unknown>;
  } else {
    // Dev-режим: через Vite proxy /api/anthropic → api.anthropic.com
    const response = await fetchWithTimeout('/api/anthropic/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
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

/** Парсит ответ LLM и строит результат. EC-11: graceful JSON parse. */
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
  const providerPrefix = provider === 'claude' ? 'CLAUDE_API_ERROR' : 'OPENAI_API_ERROR';
  if (err.startsWith(providerPrefix)) {
    const [, status] = err.split(':');
    handleAPIError(parseInt(status, 10), err, provider);
  }
  throw new LLMError(`Ошибка Tauri: ${err}`, 'API_ERROR');
}

/** Обработка HTTP-ошибок API. */
function handleAPIError(status: number, body: string, provider: LLMProvider): never {
  const providerName = provider === 'claude' ? 'Claude' : 'OpenAI';
  if (status === 401) throw new LLMError(`Невалидный API-ключ ${providerName}.`, 'INVALID_KEY');
  if (status === 429) throw new LLMError(`Превышен лимит запросов ${providerName}. Повторная попытка...`, 'RATE_LIMIT');
  if (status === 402 || body.includes('insufficient')) {
    throw new LLMError(`Недостаточно средств на аккаунте ${providerName}.`, 'INSUFFICIENT_FUNDS');
  }
  if (status >= 500) throw new LLMError(`Ошибка сервера ${providerName} (${status}).`, 'SERVER_ERROR');
  throw new LLMError(`Ошибка ${providerName} API: ${status} — ${body.slice(0, 200)}`, 'API_ERROR');
}

/**
 * Проверяет валидность API-ключа Claude.
 * В Tauri — через Rust backend. В dev — через Vite proxy.
 */
export async function validateClaudeKey(
  apiKey: string,
): Promise<{ valid: boolean; error?: string }> {
  try {
    if (isTauri()) {
      const valid = await invoke<boolean>('validate_claude_key', { apiKey });
      return valid ? { valid: true } : { valid: false, error: 'Невалидный API-ключ' };
    }
    const response = await fetch('/api/anthropic/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
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

/** Кастомная ошибка LLM */
export class LLMError extends Error {
  constructor(
    message: string,
    public code:
      | 'INVALID_KEY'
      | 'RATE_LIMIT'
      | 'INSUFFICIENT_FUNDS'
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

/** fetch с таймаутом (только для dev-режима). */
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
