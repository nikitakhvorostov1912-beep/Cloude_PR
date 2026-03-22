import { describe, it, expect, beforeEach, vi } from 'vitest';
import { saveApiKey, loadApiKey, loadAllApiKeys, deleteApiKey } from '@/services/keys.service';

// Ensure we're in dev mode (no __TAURI_INTERNALS__ in window)
describe('keys.service (dev mode - sessionStorage)', () => {
  beforeEach(() => {
    sessionStorage.clear();
    // Ensure Tauri is not detected
    delete (window as Record<string, unknown>).__TAURI_INTERNALS__;
  });

  describe('saveApiKey', () => {
    it('saves openai key to sessionStorage', async () => {
      await saveApiKey('openai', 'sk-test-key-12345678901234567890');
      const raw = sessionStorage.getItem('aether_dev_keys');
      const keys = JSON.parse(raw!);
      expect(keys.openaiKey).toBe('sk-test-key-12345678901234567890');
    });

    it('saves claude key to sessionStorage', async () => {
      await saveApiKey('claude', 'sk-ant-test-key-12345678901234567890');
      const raw = sessionStorage.getItem('aether_dev_keys');
      const keys = JSON.parse(raw!);
      expect(keys.claudeKey).toBe('sk-ant-test-key-12345678901234567890');
    });

    it('preserves existing keys when saving new one', async () => {
      await saveApiKey('openai', 'sk-openai-key-12345678901234567890');
      await saveApiKey('claude', 'sk-ant-claude-key-12345678901234567890');
      const raw = sessionStorage.getItem('aether_dev_keys');
      const keys = JSON.parse(raw!);
      expect(keys.openaiKey).toBe('sk-openai-key-12345678901234567890');
      expect(keys.claudeKey).toBe('sk-ant-claude-key-12345678901234567890');
    });
  });

  describe('loadApiKey', () => {
    it('returns empty string when no key stored', async () => {
      const key = await loadApiKey('openai');
      expect(key).toBe('');
    });

    it('loads saved openai key', async () => {
      await saveApiKey('openai', 'sk-openai-stored-12345678901234567890');
      const key = await loadApiKey('openai');
      expect(key).toBe('sk-openai-stored-12345678901234567890');
    });

    it('loads saved claude key', async () => {
      await saveApiKey('claude', 'sk-ant-stored-12345678901234567890');
      const key = await loadApiKey('claude');
      expect(key).toBe('sk-ant-stored-12345678901234567890');
    });

    it('returns empty string for invalid JSON in sessionStorage', async () => {
      sessionStorage.setItem('aether_dev_keys', 'invalid-json{');
      const key = await loadApiKey('openai');
      expect(key).toBe('');
    });
  });

  describe('loadAllApiKeys', () => {
    it('returns both keys', async () => {
      await saveApiKey('openai', 'sk-both-openai-12345678901234567890');
      await saveApiKey('claude', 'sk-ant-both-claude-12345678901234567890');
      const keys = await loadAllApiKeys();
      expect(keys.openaiKey).toBe('sk-both-openai-12345678901234567890');
      expect(keys.claudeKey).toBe('sk-ant-both-claude-12345678901234567890');
    });

    it('returns empty strings when no keys stored', async () => {
      const keys = await loadAllApiKeys();
      expect(keys.openaiKey).toBe('');
      expect(keys.claudeKey).toBe('');
    });
  });

  describe('deleteApiKey', () => {
    it('deletes openai key', async () => {
      await saveApiKey('openai', 'sk-to-delete-12345678901234567890');
      await deleteApiKey('openai');
      const key = await loadApiKey('openai');
      expect(key).toBe('');
    });

    it('deletes claude key without affecting openai', async () => {
      await saveApiKey('openai', 'sk-keep-openai-12345678901234567890');
      await saveApiKey('claude', 'sk-ant-delete-me-12345678901234567890');
      await deleteApiKey('claude');
      expect(await loadApiKey('openai')).toBe('sk-keep-openai-12345678901234567890');
      expect(await loadApiKey('claude')).toBe('');
    });
  });
});
