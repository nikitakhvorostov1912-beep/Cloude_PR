import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useSettingsStore } from '@/stores/settings.store';
import { DEFAULT_SETTINGS } from '@/types/api.types';

// Mock keys.service
vi.mock('@/services/keys.service', () => ({
  saveApiKey: vi.fn().mockResolvedValue(undefined),
  loadAllApiKeys: vi.fn().mockResolvedValue({ openaiKey: '', claudeKey: '' }),
}));

function resetStore() {
  useSettingsStore.setState({
    ...DEFAULT_SETTINGS,
    apiKeys: { openaiKey: '', claudeKey: '' },
    keysLoaded: false,
  });
}

describe('useSettingsStore', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('uses DEFAULT_SETTINGS values', () => {
      const s = useSettingsStore.getState();
      expect(s.llmProvider).toBe('claude');
      expect(s.soundEnabled).toBe(true);
      expect(s.soundVolume).toBe(0.7);
      expect(s.maxFileSizeMb).toBe(500);
      expect(s.onboardingCompleted).toBe(false);
      expect(s.apiKeys).toEqual({ openaiKey: '', claudeKey: '' });
      expect(s.keysLoaded).toBe(false);
    });
  });

  describe('setLLMProvider', () => {
    it('switches to openai', () => {
      useSettingsStore.getState().setLLMProvider('openai');
      expect(useSettingsStore.getState().llmProvider).toBe('openai');
    });

    it('switches to claude', () => {
      useSettingsStore.getState().setLLMProvider('openai');
      useSettingsStore.getState().setLLMProvider('claude');
      expect(useSettingsStore.getState().llmProvider).toBe('claude');
    });
  });

  describe('setSoundEnabled', () => {
    it('disables sound', () => {
      useSettingsStore.getState().setSoundEnabled(false);
      expect(useSettingsStore.getState().soundEnabled).toBe(false);
    });

    it('re-enables sound', () => {
      useSettingsStore.getState().setSoundEnabled(false);
      useSettingsStore.getState().setSoundEnabled(true);
      expect(useSettingsStore.getState().soundEnabled).toBe(true);
    });
  });

  describe('setSoundVolume', () => {
    it('sets volume to 0.5', () => {
      useSettingsStore.getState().setSoundVolume(0.5);
      expect(useSettingsStore.getState().soundVolume).toBe(0.5);
    });

    it('sets volume to 0', () => {
      useSettingsStore.getState().setSoundVolume(0);
      expect(useSettingsStore.getState().soundVolume).toBe(0);
    });
  });

  describe('setOnboardingCompleted', () => {
    it('marks onboarding complete', () => {
      useSettingsStore.getState().setOnboardingCompleted(true);
      expect(useSettingsStore.getState().onboardingCompleted).toBe(true);
    });
  });

  describe('setApiKey', () => {
    it('saves openai key and updates state', async () => {
      const { saveApiKey } = await import('@/services/keys.service');
      await useSettingsStore.getState().setApiKey('openaiKey', 'sk-test-key-12345678901234567890');
      expect(saveApiKey).toHaveBeenCalledWith('openai', 'sk-test-key-12345678901234567890');
      expect(useSettingsStore.getState().apiKeys.openaiKey).toBe('sk-test-key-12345678901234567890');
    });

    it('saves claude key and updates state', async () => {
      const { saveApiKey } = await import('@/services/keys.service');
      await useSettingsStore.getState().setApiKey('claudeKey', 'sk-ant-test-key-12345678901234');
      expect(saveApiKey).toHaveBeenCalledWith('claude', 'sk-ant-test-key-12345678901234');
      expect(useSettingsStore.getState().apiKeys.claudeKey).toBe('sk-ant-test-key-12345678901234');
    });
  });

  describe('loadKeys', () => {
    it('loads keys from storage', async () => {
      const { loadAllApiKeys } = await import('@/services/keys.service');
      vi.mocked(loadAllApiKeys).mockResolvedValue({
        openaiKey: 'sk-loaded-key-123456789012345678',
        claudeKey: 'sk-ant-loaded-key-12345678901234',
      });
      await useSettingsStore.getState().loadKeys();
      const s = useSettingsStore.getState();
      expect(s.apiKeys.openaiKey).toBe('sk-loaded-key-123456789012345678');
      expect(s.keysLoaded).toBe(true);
    });

    it('does not reload if already loaded', async () => {
      const { loadAllApiKeys } = await import('@/services/keys.service');
      useSettingsStore.setState({ keysLoaded: true });
      await useSettingsStore.getState().loadKeys();
      expect(loadAllApiKeys).not.toHaveBeenCalled();
    });
  });

  describe('hasValidKeys', () => {
    it('returns false with empty keys', () => {
      expect(useSettingsStore.getState().hasValidKeys()).toBe(false);
    });

    it('returns false with invalid openai key', () => {
      useSettingsStore.setState({
        apiKeys: { openaiKey: 'invalid', claudeKey: 'sk-ant-valid-key-12345678901234' },
      });
      expect(useSettingsStore.getState().hasValidKeys()).toBe(false);
    });

    it('returns true for openai provider with valid openai key', () => {
      useSettingsStore.setState({
        llmProvider: 'openai',
        apiKeys: { openaiKey: 'sk-valid-openai-key-123456789012345', claudeKey: '' },
      });
      expect(useSettingsStore.getState().hasValidKeys()).toBe(true);
    });

    it('returns false for claude provider with only openai key', () => {
      useSettingsStore.setState({
        llmProvider: 'claude',
        apiKeys: { openaiKey: 'sk-valid-openai-key-123456789012345', claudeKey: '' },
      });
      expect(useSettingsStore.getState().hasValidKeys()).toBe(false);
    });

    it('returns true for claude provider with both valid keys', () => {
      useSettingsStore.setState({
        llmProvider: 'claude',
        apiKeys: {
          openaiKey: 'sk-valid-openai-key-123456789012345',
          claudeKey: 'sk-ant-valid-claude-key-12345678901',
        },
      });
      expect(useSettingsStore.getState().hasValidKeys()).toBe(true);
    });
  });
});
