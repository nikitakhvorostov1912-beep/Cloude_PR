import type { LLMProvider, STTProvider } from '@/types/api.types';

/** Модели AI */
export const AI_MODELS = {
  claudeDefault: 'claude-sonnet-4-6',
  claudeLight: 'claude-haiku-4-5-20251001',
  openaiDefault: 'gpt-4o',
  geminiDefault: 'gemini-2.5-flash',
  groqDefault: 'qwen/qwen3-32b',
  deepseekDefault: 'deepseek-chat',
  mimoDefault: 'mimo-v2-flash',
  cerebrasDefault: 'llama-3.3-70b',
  mistralDefault: 'mistral-small-latest',
  openrouterDefault: 'qwen/qwen3-32b:free',
  whisperOpenai: 'whisper-1',
  whisperGroq: 'whisper-large-v3',
} as const;

/** Модели по умолчанию для каждого LLM провайдера */
export const DEFAULT_LLM_MODELS: Record<LLMProvider, string> = {
  claude: AI_MODELS.claudeDefault,
  openai: AI_MODELS.openaiDefault,
  gemini: AI_MODELS.geminiDefault,
  groq: AI_MODELS.groqDefault,
  deepseek: AI_MODELS.deepseekDefault,
  mimo: AI_MODELS.mimoDefault,
  cerebras: AI_MODELS.cerebrasDefault,
  mistral: AI_MODELS.mistralDefault,
  openrouter: AI_MODELS.openrouterDefault,
};

/** Модели по умолчанию для каждого STT провайдера */
export const DEFAULT_STT_MODELS: Record<STTProvider, string> = {
  openai: AI_MODELS.whisperOpenai,
  groq: AI_MODELS.whisperGroq,
  gemini: 'gemini-2.5-flash',
};

/** Base URL для OpenAI-совместимых провайдеров (Tauri mode) */
export const PROVIDER_BASE_URLS: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  gemini: 'https://generativelanguage.googleapis.com/v1beta/openai',
  groq: 'https://api.groq.com/openai/v1',
  deepseek: 'https://api.deepseek.com/v1',
  mimo: 'https://api.xiaomimimo.com/v1',
  cerebras: 'https://api.cerebras.ai/v1',
  mistral: 'https://api.mistral.ai/v1',
  openrouter: 'https://openrouter.ai/api/v1',
};

/** API endpoints для dev-режима (Vite proxy) */
export const API_ENDPOINTS = {
  // Anthropic (свой формат, не OpenAI-совместимый)
  anthropicMessages: '/api/anthropic/v1/messages',
  // OpenAI
  openaiCompletions: '/api/openai/v1/chat/completions',
  openaiTranscriptions: '/api/openai/v1/audio/transcriptions',
  openaiModels: '/api/openai/v1/models',
  // Gemini (OpenAI-совместимый)
  geminiCompletions: '/api/gemini/v1/chat/completions',
  // Groq (OpenAI-совместимый)
  groqCompletions: '/api/groq/v1/chat/completions',
  groqTranscriptions: '/api/groq/v1/audio/transcriptions',
  // DeepSeek (OpenAI-совместимый)
  deepseekCompletions: '/api/deepseek/v1/chat/completions',
  // Xiaomi MiMo (OpenAI-совместимый)
  mimoCompletions: '/api/mimo/v1/chat/completions',
  // Cerebras (OpenAI-совместимый)
  cerebrasCompletions: '/api/cerebras/v1/chat/completions',
  // Mistral (OpenAI-совместимый)
  mistralCompletions: '/api/mistral/v1/chat/completions',
  // OpenRouter (OpenAI-совместимый)
  openrouterCompletions: '/api/openrouter/v1/chat/completions',
} as const;

/** Dev proxy endpoint для LLM по провайдеру */
export const LLM_DEV_ENDPOINTS: Record<LLMProvider, string> = {
  claude: API_ENDPOINTS.anthropicMessages,
  openai: API_ENDPOINTS.openaiCompletions,
  gemini: API_ENDPOINTS.geminiCompletions,
  groq: API_ENDPOINTS.groqCompletions,
  deepseek: API_ENDPOINTS.deepseekCompletions,
  mimo: API_ENDPOINTS.mimoCompletions,
  cerebras: API_ENDPOINTS.cerebrasCompletions,
  mistral: API_ENDPOINTS.mistralCompletions,
  openrouter: API_ENDPOINTS.openrouterCompletions,
};

/** Dev proxy endpoint для STT по провайдеру */
export const STT_DEV_ENDPOINTS: Record<STTProvider, string> = {
  openai: API_ENDPOINTS.openaiTranscriptions,
  groq: API_ENDPOINTS.groqTranscriptions,
  gemini: '/api/gemini/v1/audio/transcriptions', // Gemini использует свой API, не Whisper
};

/** Anthropic API версия */
export const ANTHROPIC_VERSION = '2023-06-01';

/** Человекочитаемые имена провайдеров */
export const PROVIDER_NAMES: Record<LLMProvider | STTProvider, string> = {
  claude: 'Claude (Anthropic)',
  openai: 'OpenAI',
  gemini: 'Google Gemini',
  groq: 'Groq',
  deepseek: 'DeepSeek',
  mimo: 'Xiaomi MiMo',
  cerebras: 'Cerebras',
  mistral: 'Mistral',
  openrouter: 'OpenRouter',
};

/** Regex для валидации API-ключей */
export const KEY_PATTERNS: Record<LLMProvider | STTProvider, RegExp> = {
  openai: /^sk-[A-Za-z0-9_-]{20,}$/,
  claude: /^sk-ant-[A-Za-z0-9_-]{20,}$/,
  gemini: /^AI[A-Za-z0-9_-]{20,}$/,
  groq: /^gsk_[A-Za-z0-9]{20,}$/,
  deepseek: /^sk-[A-Za-z0-9]{20,}$/,
  mimo: /^sk-[A-Za-z0-9]{20,}$/,
  cerebras: /^csk-[A-Za-z0-9_-]{20,}$/,
  mistral: /^[A-Za-z0-9]{20,}$/,
  openrouter: /^sk-or-[A-Za-z0-9_-]{20,}$/,
};

/** UI константы */
export const UI = {
  toastTimeout: 4000,
  dashboardMeetingsLimit: 5,
} as const;

/** Стоимость моделей за 1M токенов (USD), 0 = бесплатно */
export const MODEL_COSTS: Record<string, number> = {
  'gpt-4o': 7.5,
  'gpt-4o-mini': 0.3,
  'claude-sonnet-4-6': 9.0,
  'claude-haiku-4-5-20251001': 1.0,
  'gemini-2.5-flash': 0,
  'qwen/qwen3-32b': 0,
  'whisper-large-v3': 0,
  'deepseek-chat': 0.28,
  'mimo-v2-flash': 0.09,
  'llama-3.3-70b': 0,
  'mistral-small-latest': 0,
  'qwen/qwen3-32b:free': 0,
};

/** Информация о провайдерах для UI */
export const LLM_PROVIDER_INFO: Array<{
  id: LLMProvider;
  name: string;
  model: string;
  badge: string;
  desc: string;
}> = [
  { id: 'groq', name: 'Groq', model: 'qwen/qwen3-32b', badge: 'Бесплатно', desc: '500K токенов/день' },
  { id: 'gemini', name: 'Google Gemini', model: 'gemini-2.5-flash', badge: 'Бесплатно', desc: '250 запросов/день' },
  { id: 'deepseek', name: 'DeepSeek', model: 'deepseek-chat', badge: '~Бесплатно', desc: '5M бонусных токенов' },
  { id: 'mimo', name: 'Xiaomi MiMo', model: 'mimo-v2-flash', badge: '~Бесплатно', desc: '$0.09/1M токенов' },
  { id: 'cerebras', name: 'Cerebras', model: 'llama-3.3-70b', badge: 'Бесплатно', desc: '1M токенов/день, сверхбыстрый' },
  { id: 'mistral', name: 'Mistral', model: 'mistral-small-latest', badge: 'Бесплатно', desc: '1B токенов/месяц' },
  { id: 'openrouter', name: 'OpenRouter', model: 'qwen/qwen3-32b:free', badge: 'Бесплатно', desc: '29 бесплатных моделей' },
];

/** Информация о STT провайдерах для UI */
export const STT_PROVIDER_INFO: Array<{
  id: STTProvider;
  name: string;
  model: string;
  badge: string;
  desc: string;
}> = [
  { id: 'groq', name: 'Groq Whisper', model: 'whisper-large-v3', badge: 'Бесплатно', desc: '~8ч аудио/день, 189× real-time' },
  { id: 'gemini', name: 'Google Gemini', model: 'gemini-2.5-flash', badge: 'Бесплатно', desc: 'Мультимодальная транскрипция, 250 RPD' },
  { id: 'openai', name: 'OpenAI Whisper', model: 'whisper-1', badge: 'Платно', desc: '$0.006/мин, высокая точность' },
];

/** Доступные модели для каждого LLM провайдера */
export const PROVIDER_MODELS: Record<LLMProvider, Array<{ id: string; name: string }>> = {
  groq: [
    { id: 'qwen/qwen3-32b', name: 'Qwen3-32B' },
    { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B' },
    { id: 'llama-3.1-8b-instant', name: 'Llama 3.1 8B (быстрая)' },
    { id: 'meta-llama/llama-4-scout-17b-16e-instruct', name: 'Llama 4 Scout 17B' },
  ],
  gemini: [
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
  ],
  deepseek: [
    { id: 'deepseek-chat', name: 'DeepSeek Chat' },
  ],
  mimo: [
    { id: 'mimo-v2-flash', name: 'MiMo v2 Flash' },
  ],
  cerebras: [
    { id: 'llama-3.3-70b', name: 'Llama 3.3 70B' },
    { id: 'qwen-3-32b', name: 'Qwen3 32B' },
  ],
  mistral: [
    { id: 'mistral-small-latest', name: 'Mistral Small 3.1' },
    { id: 'mistral-medium-latest', name: 'Mistral Medium' },
  ],
  openrouter: [
    { id: 'qwen/qwen3-32b:free', name: 'DeepSeek V3 (бесплатно)' },
    { id: 'meta-llama/llama-3.3-70b-instruct:free', name: 'Llama 3.3 70B (бесплатно)' },
    { id: 'qwen/qwen3-32b:free', name: 'Qwen3 32B (бесплатно)' },
    { id: 'google/gemma-3-27b-it:free', name: 'Gemma 3 27B (бесплатно)' },
  ],
  claude: [],
  openai: [],
};
