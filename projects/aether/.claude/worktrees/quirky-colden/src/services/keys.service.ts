/**
 * Сервис безопасного хранения API-ключей.
 * В Tauri: Stronghold (зашифрованное хранилище).
 * В dev: sessionStorage (только для разработки, ключи не сохраняются между сессиями).
 */

import { appDataDir } from '@tauri-apps/api/path';

const isTauri = (): boolean => '__TAURI_INTERNALS__' in window;

// Stronghold vault загружается лениво при первом обращении
let vaultStore: Awaited<ReturnType<typeof loadVaultStore>> | null = null;

/** Внутренний пароль vault — не связан с данными пользователя */
const VAULT_PASSWORD = 'aether-api-keys-vault-2026';
const STORE_NAME = 'api-keys';
const KEY_OPENAI = 'openai_key';
const KEY_CLAUDE = 'claude_key';

async function loadVaultStore() {
  const { Stronghold } = await import('@tauri-apps/plugin-stronghold');
  const dataDir = await appDataDir();
  const stronghold = await Stronghold.load(
    `${dataDir}/aether.stronghold`,
    VAULT_PASSWORD,
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
  if (!vaultStore) {
    vaultStore = await loadVaultStore();
  }
  return vaultStore;
}

// ─── Dev fallback (sessionStorage) ───────────────────────────────────────────

const DEV_STORE_KEY = 'aether_dev_keys';

function devGetKeys(): { openaiKey: string; claudeKey: string } {
  try {
    const raw = sessionStorage.getItem(DEV_STORE_KEY);
    return raw ? JSON.parse(raw) : { openaiKey: '', claudeKey: '' };
  } catch {
    return { openaiKey: '', claudeKey: '' };
  }
}

function devSetKey(name: 'openaiKey' | 'claudeKey', value: string): void {
  const current = devGetKeys();
  sessionStorage.setItem(DEV_STORE_KEY, JSON.stringify({ ...current, [name]: value }));
}

// ─── Public API ───────────────────────────────────────────────────────────────

/** Сохраняет API-ключ в зашифрованное хранилище. */
export async function saveApiKey(
  provider: 'openai' | 'claude',
  key: string,
): Promise<void> {
  if (!isTauri()) {
    devSetKey(provider === 'openai' ? 'openaiKey' : 'claudeKey', key);
    return;
  }

  const { store, stronghold } = await getVaultStore();
  const storeKey = provider === 'openai' ? KEY_OPENAI : KEY_CLAUDE;
  const bytes = Array.from(new TextEncoder().encode(key));
  await store.insert(storeKey, bytes);
  await stronghold.save();
}

/** Читает API-ключ из зашифрованного хранилища. */
export async function loadApiKey(provider: 'openai' | 'claude'): Promise<string> {
  if (!isTauri()) {
    const keys = devGetKeys();
    return provider === 'openai' ? keys.openaiKey : keys.claudeKey;
  }

  try {
    const { store } = await getVaultStore();
    const storeKey = provider === 'openai' ? KEY_OPENAI : KEY_CLAUDE;
    const bytes = await store.get(storeKey);
    if (!bytes) return '';
    return new TextDecoder().decode(new Uint8Array(bytes));
  } catch {
    return '';
  }
}

/** Загружает оба ключа сразу. */
export async function loadAllApiKeys(): Promise<{ openaiKey: string; claudeKey: string }> {
  const [openaiKey, claudeKey] = await Promise.all([
    loadApiKey('openai'),
    loadApiKey('claude'),
  ]);
  return { openaiKey, claudeKey };
}

/** Удаляет API-ключ из хранилища. */
export async function deleteApiKey(provider: 'openai' | 'claude'): Promise<void> {
  if (!isTauri()) {
    devSetKey(provider === 'openai' ? 'openaiKey' : 'claudeKey', '');
    return;
  }

  try {
    const { store, stronghold } = await getVaultStore();
    const storeKey = provider === 'openai' ? KEY_OPENAI : KEY_CLAUDE;
    await store.remove(storeKey);
    await stronghold.save();
  } catch {
    // Ключ не существовал — ок
  }
}
