import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AppSettings, APIKeys, LLMProvider } from '@/types/api.types';
import { DEFAULT_SETTINGS } from '@/types/api.types';

interface SettingsState extends AppSettings {
  apiKeys: APIKeys;
  setLLMProvider: (provider: LLMProvider) => void;
  setStoragePath: (path: string) => void;
  setMaxFileSize: (mb: number) => void;
  setSoundEnabled: (enabled: boolean) => void;
  setSoundVolume: (volume: number) => void;
  setOnboardingCompleted: (completed: boolean) => void;
  setApiKey: (provider: keyof APIKeys, key: string) => void;
  hasValidKeys: () => boolean;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_SETTINGS,
      apiKeys: {
        openaiKey: '',
        claudeKey: '',
      },
      setLLMProvider: (provider) => set({ llmProvider: provider }),
      setStoragePath: (path) => set({ storagePath: path }),
      setMaxFileSize: (mb) => set({ maxFileSizeMb: mb }),
      setSoundEnabled: (enabled) => set({ soundEnabled: enabled }),
      setSoundVolume: (volume) => set({ soundVolume: volume }),
      setOnboardingCompleted: (completed) => set({ onboardingCompleted: completed }),
      setApiKey: (provider, key) =>
        set((state) => ({
          apiKeys: { ...state.apiKeys, [provider]: key },
        })),
      hasValidKeys: () => {
        const { apiKeys } = get();
        return apiKeys.openaiKey.length > 10 || apiKeys.claudeKey.length > 10;
      },
    }),
    {
      name: 'aether-settings',
    }
  )
);
