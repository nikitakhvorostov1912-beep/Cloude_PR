export type LLMProvider = 'claude' | 'openai';

export interface APIKeys {
  openaiKey: string;
  claudeKey: string;
}

export interface AppSettings {
  llmProvider: LLMProvider;
  storagePath: string;
  maxFileSizeMb: number;
  soundEnabled: boolean;
  soundVolume: number;
  onboardingCompleted: boolean;
}

export const DEFAULT_SETTINGS: AppSettings = {
  llmProvider: 'claude',
  storagePath: '',
  maxFileSizeMb: 500,
  soundEnabled: true,
  soundVolume: 0.7,
  onboardingCompleted: false,
};
