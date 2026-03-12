/**
 * Абстрактный LLM-сервис для Claude и OpenAI.
 * Обрабатывает edge cases: EC-09 (API ошибка), EC-11 (невалидный JSON).
 */

import type { LLMProvider } from '@/types/api.types';
import type { ArtifactType } from '@/types/artifact.types';
import type { BuiltPrompt } from '@/lib/prompts';
import { tryParseJSON } from '@/lib/validators';

/** OpenAI Chat Completions API */
const OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions';

/** Anthropic Messages API */
const ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';

/** Retry конфигурация */
const MAX_RETRIES = 3;
const RETRY_DELAYS = [5_000, 15_000, 30_000];

/** Модели по умолчанию */
const DEFAULT_MODELS: Record<LLMProvider, string> = {
  claude: 'claude-sonnet-4-20250514',
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
 * Поддерживает стриминг и retry.
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

      const result = provider === 'openai'
        ? await callOpenAI(prompt, apiKey, model, callbacks)
        : await callClaude(prompt, apiKey, model, callbacks);

      return result;
    } catch (error) {
      if (error instanceof LLMError && error.code === 'INVALID_KEY') {
        throw error; // Не повторяем для невалидного ключа
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
 * Генерирует несколько артефактов параллельно.
 * Каждый промпт независим (EC-10: частичный результат).
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

  // Запускаем все промпты параллельно (до 3 одновременно)
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

    if (running.length > 0) {
      await Promise.race(running);
    }
  }

  return results;
}

/**
 * Вызов OpenAI Chat Completions API.
 * Поддерживает CORS из браузера.
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

  const response = await fetch(OPENAI_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    handleAPIError(response.status, errorText, 'openai');
  }

  const data = await response.json();
  const text = data.choices?.[0]?.message?.content || '';
  const usage = data.usage || {};

  callbacks?.onToken?.(text);

  return parseAndBuildResult(text, {
    inputTokens: usage.prompt_tokens || 0,
    outputTokens: usage.completion_tokens || 0,
  }, model, 'openai', prompt.artifactType);
}

/**
 * Вызов Anthropic Messages API.
 * Примечание: Anthropic API не поддерживает CORS из браузера.
 * В Tauri используется plugin-http. В dev-режиме — через Vite proxy.
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
    messages: [
      { role: 'user', content: prompt.user },
    ],
    temperature: prompt.temperature,
  };

  // В dev-режиме используем proxy (/api/anthropic → api.anthropic.com)
  // В Tauri используем прямой URL
  const isTauri = '__TAURI_INTERNALS__' in window;
  const apiUrl = isTauri ? ANTHROPIC_API_URL : '/api/anthropic/v1/messages';

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'x-api-key': apiKey,
    'anthropic-version': '2023-06-01',
  };

  // Для Tauri — прямой запрос (нет CORS ограничений)
  // Для Vite dev — через proxy (обходит CORS)
  const response = await fetch(apiUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    handleAPIError(response.status, errorText, 'claude');
  }

  const data = await response.json();
  const text = data.content?.[0]?.text || '';
  const usage = data.usage || {};

  callbacks?.onToken?.(text);

  return parseAndBuildResult(text, {
    inputTokens: usage.input_tokens || 0,
    outputTokens: usage.output_tokens || 0,
  }, model, 'claude', prompt.artifactType);
}

/**
 * Парсит ответ LLM и строит результат.
 * EC-11: retry парсинга JSON с автоисправлением.
 */
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

/**
 * Обработка HTTP-ошибок API.
 */
function handleAPIError(status: number, body: string, provider: LLMProvider): never {
  const providerName = provider === 'claude' ? 'Claude' : 'OpenAI';

  if (status === 401) {
    throw new LLMError(`Невалидный API-ключ ${providerName}.`, 'INVALID_KEY');
  }
  if (status === 429) {
    throw new LLMError(`Превышен лимит запросов ${providerName}. Повторная попытка...`, 'RATE_LIMIT');
  }
  if (status === 402 || body.includes('insufficient')) {
    throw new LLMError(`Недостаточно средств на аккаунте ${providerName}.`, 'INSUFFICIENT_FUNDS');
  }
  if (status >= 500) {
    throw new LLMError(`Ошибка сервера ${providerName} (${status}).`, 'SERVER_ERROR');
  }

  throw new LLMError(
    `Ошибка ${providerName} API: ${status} — ${body.slice(0, 200)}`,
    'API_ERROR',
  );
}

/**
 * Проверяет валидность API-ключа Claude.
 */
export async function validateClaudeKey(apiKey: string): Promise<{ valid: boolean; error?: string }> {
  try {
    const isTauri = '__TAURI_INTERNALS__' in window;
    const apiUrl = isTauri ? ANTHROPIC_API_URL : '/api/anthropic/v1/messages';

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
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
    public code: 'INVALID_KEY' | 'RATE_LIMIT' | 'INSUFFICIENT_FUNDS' | 'SERVER_ERROR' | 'API_ERROR' | 'MAX_RETRIES_EXCEEDED',
  ) {
    super(message);
    this.name = 'LLMError';
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
