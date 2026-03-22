import { vi, afterEach } from 'vitest';

// ─── Mock Tauri APIs ───────────────────────────────────────────────────────────

vi.mock('@tauri-apps/api/path', () => ({
  appDataDir: vi.fn().mockResolvedValue('/mock/app/data'),
}));

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn().mockResolvedValue(null),
}));

vi.mock('@tauri-apps/api/event', () => ({
  listen: vi.fn().mockResolvedValue(() => {}),
  emit: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('@tauri-apps/plugin-stronghold', () => ({
  Stronghold: {
    load: vi.fn().mockResolvedValue({
      loadClient: vi.fn().mockResolvedValue({
        getStore: vi.fn().mockReturnValue({
          insert: vi.fn().mockResolvedValue(undefined),
          get: vi.fn().mockResolvedValue(null),
          remove: vi.fn().mockResolvedValue(undefined),
        }),
      }),
      createClient: vi.fn().mockResolvedValue({
        getStore: vi.fn().mockReturnValue({
          insert: vi.fn().mockResolvedValue(undefined),
          get: vi.fn().mockResolvedValue(null),
          remove: vi.fn().mockResolvedValue(undefined),
        }),
      }),
      save: vi.fn().mockResolvedValue(undefined),
    }),
  },
}));

vi.mock('@tauri-apps/plugin-opener', () => ({
  open: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('@tauri-apps/plugin-sql', () => ({
  default: {
    load: vi.fn().mockResolvedValue({
      execute: vi.fn().mockResolvedValue({ rowsAffected: 1 }),
      select: vi.fn().mockResolvedValue([]),
    }),
  },
}));

// ─── Mock Howler ───────────────────────────────────────────────────────────────

vi.mock('howler', () => ({
  Howl: vi.fn().mockImplementation(() => ({
    play: vi.fn(),
    stop: vi.fn(),
    volume: vi.fn(),
    on: vi.fn(),
  })),
}));

// ─── Mock localStorage / sessionStorage ───────────────────────────────────────

function makeStorageMock() {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = String(value); },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
    get length() { return Object.keys(store).length; },
    key: (i: number) => Object.keys(store)[i] ?? null,
    _reset: () => { store = {}; },
  };
}

export const localStorageMock = makeStorageMock();
export const sessionStorageMock = makeStorageMock();

// Install storage mocks on globalThis (works in both node and jsdom environments)
try {
  Object.defineProperty(globalThis, 'localStorage', {
    value: localStorageMock,
    writable: true,
    configurable: true,
  });
} catch {
  // jsdom may already have localStorage defined, try direct assignment
  (globalThis as Record<string, unknown>).localStorage = localStorageMock;
}

try {
  Object.defineProperty(globalThis, 'sessionStorage', {
    value: sessionStorageMock,
    writable: true,
    configurable: true,
  });
} catch {
  (globalThis as Record<string, unknown>).sessionStorage = sessionStorageMock;
}

// ─── Mock URL static methods (safe - works in node and jsdom) ─────────────────

if (typeof URL !== 'undefined') {
  URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
  URL.revokeObjectURL = vi.fn();
}

// ─── Cleanup ───────────────────────────────────────────────────────────────────

afterEach(() => {
  localStorageMock._reset();
  sessionStorageMock._reset();
  vi.clearAllMocks();
  // Re-apply URL mocks after clearAllMocks
  if (typeof URL !== 'undefined') {
    URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    URL.revokeObjectURL = vi.fn();
  }
});
