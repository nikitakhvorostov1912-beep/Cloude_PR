import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AppSettings, APIKeys, LLMProvider } from '@/types/api.types';
import { DEFAULT_SETTINGS } from '@/types/api.types';
import { saveApiKey, loadAllApiKeys } from '@/services/keys.service';

interface SettingsState extends AppSettings {
  /** API-ключи в памяти (не попадают в localStorage — только через Stronghold). */
  apiKeys: APIKeys;
  keysLoaded: boolean;
  setLLMProvider: (provider: LLMProvider) => void;
  setStoragePath: (path: string) => void;
  setMaxFileSize: (mb: number) => void;
  setSoundEnabled: (enabled: boolean) => void;
  setSoundVolume: (volume: number) => void;
  setOnboardingCompleted: (completed: boolean) => void;
  /** Сохраняет ключ в Stronghold и обновляет состояние в памяти. */
  setApiKey: (provider: keyof APIKeys, key: string) => Promise<void>;
  /** Загружает ключи из Stronghold при старте приложения. */
  loadKeys: () => Promise<void>;
  hasValidKeys: () => boolean;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_SETTINGS,
      apiKeys: { openaiKey: '', claudeKey: '' },
      keysLoaded: false,

      setLLMProvider: (provider) => set({ llmProvider: provider }),
      setStoragePath: (path) => set({ storagePath: path }),
      setMaxFileSize: (mb) => set({ maxFileSizeMb: mb }),
      setSoundEnabled: (enabled) => set({ soundEnabled: enabled }),
      setSoundVolume: (volume) => set({ soundVolume: volume }),
      setOnboardingCompleted: (completed) => set({ onboardingCompleted: completed }),

      setApiKey: async (provider, key) => {
        const storageProvider = provider === 'openaiKey' ? 'openai' : 'claude';
        await saveApiKey(storageProvider, key);
        set((state) => ({
          apiKeys: { ...state.apiKeys, [provider]: key },
        }));
      },

      loadKeys: async () => {
        if (get().keysLoaded) return;
        const keys = await loadAllApiKeys();
        set({ apiKeys: keys, keysLoaded: true });
      },

      hasValidKeys: () => {
        const { apiKeys, llmProvider } = get();
        const openaiValid =
          apiKeys.openaiKey.startsWith('sk-') && apiKeys.openaiKey.length > 20;
        const claudeValid =
          apiKeys.claudeKey.startsWith('sk-ant-') && apiKeys.claudeKey.length > 20;
        if (!openaiValid) return false;
        if (llmProvider === 'claude') return claudeValid;
        return openaiValid;
      },
    }),
    {
      name: 'aether-settings',
      // API ключи намеренно исключены — хранятся в Stronghold, не в localStorage
      partialize: (state) => {
        const { apiKeys: _apiKeys, keysLoaded: _keysLoaded, ...rest } = state;
        return rest;
      },
    },
  ),
);
