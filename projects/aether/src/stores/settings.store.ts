import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AppSettings, APIKeys, LLMProvider, STTProvider, ProviderRoutingMode } from '@/types/api.types';
import { DEFAULT_SETTINGS } from '@/types/api.types';
import { saveApiKey, loadAllApiKeys, type KeyProvider } from '@/services/keys.service';

interface SettingsState extends AppSettings {
  /** API-ключи в памяти (не попадают в localStorage — только через Stronghold). */
  apiKeys: APIKeys;
  keysLoaded: boolean;
  setLLMProvider: (provider: LLMProvider) => void;
  setLLMModel: (model: string) => void;
  setSTTProvider: (provider: STTProvider) => void;
  setStoragePath: (path: string) => void;
  setMaxFileSize: (mb: number) => void;
  setSoundEnabled: (enabled: boolean) => void;
  setSoundVolume: (volume: number) => void;
  setOnboardingCompleted: (completed: boolean) => void;
  setRoutingMode: (mode: ProviderRoutingMode) => void;
  /** Сохраняет ключ в Stronghold и обновляет состояние в памяти. */
  setApiKey: (provider: keyof APIKeys, key: string) => Promise<void>;
  /** Загружает ключи из Stronghold при старте приложения. */
  loadKeys: () => Promise<void>;
}

/** Маппинг поля APIKeys → провайдер для Stronghold */
const FIELD_TO_PROVIDER: Record<keyof APIKeys, KeyProvider> = {
  openaiKey: 'openai',
  claudeKey: 'claude',
  geminiKey: 'gemini',
  groqKey: 'groq',
  deepseekKey: 'deepseek',
  mimoKey: 'mimo',
  cerebrasKey: 'cerebras',
  mistralKey: 'mistral',
  openrouterKey: 'openrouter',
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_SETTINGS,
      apiKeys: { openaiKey: '', claudeKey: '', geminiKey: '', groqKey: '', deepseekKey: '', mimoKey: '', cerebrasKey: '', mistralKey: '', openrouterKey: '' },
      keysLoaded: false,

      setLLMProvider: (provider) => set({ llmProvider: provider, llmModel: '' }),
      setLLMModel: (model) => set({ llmModel: model }),
      setSTTProvider: (provider) => set({ sttProvider: provider }),
      setStoragePath: (path) => set({ storagePath: path }),
      setMaxFileSize: (mb) => set({ maxFileSizeMb: mb }),
      setSoundEnabled: (enabled) => set({ soundEnabled: enabled }),
      setSoundVolume: (volume) => set({ soundVolume: volume }),
      setOnboardingCompleted: (completed) => set({ onboardingCompleted: completed }),
      setRoutingMode: (mode) => set({ routingMode: mode }),

      setApiKey: async (field, key) => {
        const storageProvider = FIELD_TO_PROVIDER[field];
        await saveApiKey(storageProvider, key);
        set((state) => ({
          apiKeys: { ...state.apiKeys, [field]: key },
        }));
      },

      loadKeys: async () => {
        if (get().keysLoaded) return;
        const keys = await loadAllApiKeys();
        set({ apiKeys: keys, keysLoaded: true });
      },

    }),
    {
      name: 'aether-settings',
      partialize: (state) => {
        const { apiKeys: _apiKeys, keysLoaded: _keysLoaded, ...rest } = state;
        return rest;
      },
    },
  ),
);
