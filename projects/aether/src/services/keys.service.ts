/**
 * Сервис безопасного хранения API-ключей.
 * В Tauri: Stronghold (зашифрованное хранилище).
 * В dev: sessionStorage (только для разработки).
 */

import { appDataDir } from '@tauri-apps/api/path';
import type { APIKeys } from '@/types/api.types';

const isTauri = (): boolean => '__TAURI_INTERNALS__' in window;

/** Таймаут на Stronghold операции (мс) */
const VAULT_TIMEOUT_MS = 10_000;

/** Флаг: Stronghold недоступен — используем localStorage fallback */
let strongholdFailed = false;

let vaultStorePromise: Promise<Awaited<ReturnType<typeof loadVaultStore>>> | null = null;

/** Обёртка с таймаутом для Stronghold операций */
function withTimeout<T>(promise: Promise<T>, label: string): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error(`Stronghold таймаут (${VAULT_TIMEOUT_MS / 1000}с): ${label}`)), VAULT_TIMEOUT_MS),
    ),
  ]);
}

async function getVaultPassword(): Promise<string> {
  try {
    const dataDir = await appDataDir();
    const encoder = new TextEncoder();
    const data = encoder.encode(`aether-vault-${dataDir}`);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  } catch {
    return 'aether-dev-vault-fallback';
  }
}

const STORE_NAME = 'api-keys';

/** Маппинг провайдеров на ключи в Stronghold */
const STORE_KEYS: Record<KeyProvider, string> = {
  openai: 'openai_key',
  claude: 'claude_key',
  gemini: 'gemini_key',
  groq: 'groq_key',
  deepseek: 'deepseek_key',
  mimo: 'mimo_key',
  cerebras: 'cerebras_key',
  mistral: 'mistral_key',
  openrouter: 'openrouter_key',
};

export type KeyProvider = 'openai' | 'claude' | 'gemini' | 'groq' | 'deepseek' | 'mimo' | 'cerebras' | 'mistral' | 'openrouter';

/** Маппинг KeyProvider → поле APIKeys */
const PROVIDER_TO_FIELD: Record<KeyProvider, keyof APIKeys> = {
  openai: 'openaiKey',
  claude: 'claudeKey',
  gemini: 'geminiKey',
  groq: 'groqKey',
  deepseek: 'deepseekKey',
  mimo: 'mimoKey',
  cerebras: 'cerebrasKey',
  mistral: 'mistralKey',
  openrouter: 'openrouterKey',
};

async function loadVaultStore() {
  const { Stronghold } = await import('@tauri-apps/plugin-stronghold');
  const dataDir = await appDataDir();
  const vaultPassword = await getVaultPassword();
  const stronghold = await Stronghold.load(
    `${dataDir}/aether.stronghold`,
    vaultPassword,
  );
  let client;
  try {
    client = await stronghold.loadClient(STORE_NAME);
  } catch {
    client = await stronghold.createClient(STORE_NAME);
  }
  const store = client.getStore();
  return { stronghold, store };
}

async function getVaultStore() {
  if (strongholdFailed) {
    throw new Error('Stronghold недоступен — используется fallback');
  }
  if (!vaultStorePromise) {
    vaultStorePromise = withTimeout(loadVaultStore(), 'loadVaultStore').catch((err) => {
      console.error('[Keys] Stronghold инициализация не удалась:', err);
      strongholdFailed = true;
      vaultStorePromise = null;
      throw err;
    });
  }
  return vaultStorePromise;
}

// ─── Fallback хранилище (localStorage для dev, localStorage для Stronghold-ошибок) ─

const FALLBACK_STORE_KEY = 'aether_keys_fallback';

const EMPTY_KEYS: APIKeys = {
  openaiKey: '',
  claudeKey: '',
  geminiKey: '',
  groqKey: '',
  deepseekKey: '',
  mimoKey: '',
  cerebrasKey: '',
  mistralKey: '',
  openrouterKey: '',
};

function fallbackGetKeys(): APIKeys {
  try {
    // Приоритет: localStorage (persist между сессиями), потом sessionStorage (legacy)
    const raw = localStorage.getItem(FALLBACK_STORE_KEY)
      || sessionStorage.getItem('aether_dev_keys');
    return raw ? { ...EMPTY_KEYS, ...JSON.parse(raw) } : { ...EMPTY_KEYS };
  } catch {
    return { ...EMPTY_KEYS };
  }
}

function fallbackSetKey(field: keyof APIKeys, value: string): void {
  const current = fallbackGetKeys();
  localStorage.setItem(FALLBACK_STORE_KEY, JSON.stringify({ ...current, [field]: value }));
}

// ─── Public API ───────────────────────────────────────────────────────────────

/** Сохраняет API-ключ в зашифрованное хранилище (Stronghold → fallback localStorage). */
export async function saveApiKey(
  provider: KeyProvider,
  key: string,
): Promise<void> {
  const field = PROVIDER_TO_FIELD[provider];

  if (!isTauri()) {
    fallbackSetKey(field, key);
    return;
  }

  try {
    const { store, stronghold } = await getVaultStore();
    const storeKey = STORE_KEYS[provider];
    const bytes = Array.from(new TextEncoder().encode(key));
    await withTimeout(store.insert(storeKey, bytes), `insert(${provider})`);
    await withTimeout(stronghold.save(), `save(${provider})`);
  } catch (err) {
    console.warn(`[Keys] Stronghold saveApiKey(${provider}) failed, fallback:`, err);
    fallbackSetKey(field, key);
  }
}

/** Читает API-ключ из зашифрованного хранилища (Stronghold → fallback localStorage). */
export async function loadApiKey(provider: KeyProvider): Promise<string> {
  const field = PROVIDER_TO_FIELD[provider];

  if (!isTauri()) {
    return fallbackGetKeys()[field];
  }

  try {
    const { store } = await getVaultStore();
    const storeKey = STORE_KEYS[provider];
    const bytes = await withTimeout(store.get(storeKey), `get(${provider})`);
    if (!bytes) {
      // Stronghold пуст — попробовать fallback (миграция)
      const fallbackVal = fallbackGetKeys()[field];
      return fallbackVal || '';
    }
    return new TextDecoder().decode(new Uint8Array(bytes));
  } catch (err) {
    console.warn(`[Keys] loadApiKey(${provider}) Stronghold failed, fallback:`, err);
    return fallbackGetKeys()[field] || '';
  }
}

/** Загружает все ключи сразу. */
export async function loadAllApiKeys(): Promise<APIKeys> {
  const [openaiKey, claudeKey, geminiKey, groqKey, deepseekKey, mimoKey, cerebrasKey, mistralKey, openrouterKey] = await Promise.all([
    loadApiKey('openai'),
    loadApiKey('claude'),
    loadApiKey('gemini'),
    loadApiKey('groq'),
    loadApiKey('deepseek'),
    loadApiKey('mimo'),
    loadApiKey('cerebras'),
    loadApiKey('mistral'),
    loadApiKey('openrouter'),
  ]);
  return { openaiKey, claudeKey, geminiKey, groqKey, deepseekKey, mimoKey, cerebrasKey, mistralKey, openrouterKey };
}

/** Удаляет API-ключ из хранилища. */
export async function deleteApiKey(provider: KeyProvider): Promise<void> {
  const field = PROVIDER_TO_FIELD[provider];

  if (!isTauri()) {
    fallbackSetKey(field, '');
    return;
  }

  try {
    const { store, stronghold } = await getVaultStore();
    const storeKey = STORE_KEYS[provider];
    await withTimeout(store.remove(storeKey), `remove(${provider})`);
    await withTimeout(stronghold.save(), `save-delete(${provider})`);
  } catch (err) {
    console.warn(`[Keys] deleteApiKey(${provider}) failed:`, err);
  }
  // Всегда чистим fallback тоже
  fallbackSetKey(field, '');
}
