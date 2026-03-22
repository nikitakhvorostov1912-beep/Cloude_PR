export type LLMProvider = 'claude' | 'openai' | 'gemini' | 'groq' | 'deepseek' | 'mimo' | 'cerebras' | 'mistral' | 'openrouter';
export type STTProvider = 'openai' | 'groq' | 'gemini';

export interface APIKeys {
  openaiKey: string;
  claudeKey: string;
  geminiKey: string;
  groqKey: string;
  deepseekKey: string;
  mimoKey: string;
  cerebrasKey: string;
  mistralKey: string;
  openrouterKey: string;
}

/** Режим маршрутизации провайдеров */
export type ProviderRoutingMode = 'single' | 'auto';

export interface AppSettings {
  llmProvider: LLMProvider;
  /** Кастомная модель для текущего LLM-провайдера (если не задана — берётся из DEFAULT_LLM_MODELS) */
  llmModel: string;
  sttProvider: STTProvider;
  storagePath: string;
  maxFileSizeMb: number;
  soundEnabled: boolean;
  soundVolume: number;
  onboardingCompleted: boolean;
  /** Режим маршрутизации: single — один провайдер, auto — автоматическая ротация */
  routingMode: ProviderRoutingMode;
}

export const DEFAULT_SETTINGS: AppSettings = {
  llmProvider: 'groq',
  llmModel: '',
  sttProvider: 'groq',
  storagePath: '',
  maxFileSizeMb: 500,
  soundEnabled: true,
  soundVolume: 0.7,
  onboardingCompleted: false,
  routingMode: 'auto',
};
