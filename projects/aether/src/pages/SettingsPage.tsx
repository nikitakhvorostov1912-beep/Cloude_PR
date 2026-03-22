import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton, GlassInput } from '@/components/glass';
import { useSettingsStore } from '@/stores/settings.store';
import { useUIStore } from '@/stores/ui.store';
import { useShallow } from 'zustand/react/shallow';
import { useSound } from '@/hooks/useSound';
import type { APIKeys, ProviderRoutingMode } from '@/types/api.types';
import { LLM_PROVIDER_INFO, STT_PROVIDER_INFO, PROVIDER_MODELS, DEFAULT_LLM_MODELS } from '@/lib/constants';

/** Маппинг провайдер → поле APIKeys для ввода ключа */
const PROVIDER_KEY_FIELDS: Array<{
  field: keyof APIKeys;
  provider: string;
  label: string;
  placeholder: string;
  hint?: string;
}> = [
  { field: 'groqKey', provider: 'groq', label: 'Groq', placeholder: 'gsk_...', hint: 'LLM + транскрипция (Whisper)' },
  { field: 'openaiKey', provider: 'openai', label: 'OpenAI', placeholder: 'sk-...', hint: 'Платный fallback для транскрипции' },
  { field: 'geminiKey', provider: 'gemini', label: 'Google Gemini', placeholder: 'AI...' },
  { field: 'deepseekKey', provider: 'deepseek', label: 'DeepSeek', placeholder: 'sk-...' },
  { field: 'mimoKey', provider: 'mimo', label: 'Xiaomi MiMo', placeholder: 'sk-...' },
  { field: 'cerebrasKey', provider: 'cerebras', label: 'Cerebras', placeholder: 'csk-...' },
  { field: 'mistralKey', provider: 'mistral', label: 'Mistral', placeholder: 'ключ...' },
  { field: 'openrouterKey', provider: 'openrouter', label: 'OpenRouter', placeholder: 'sk-or-...' },
];

export function SettingsPage() {
  const {
    apiKeys, llmProvider, llmModel, sttProvider, soundEnabled, soundVolume, routingMode,
    setApiKey, setLLMProvider, setLLMModel, setSTTProvider, setSoundEnabled, setSoundVolume, setRoutingMode,
  } = useSettingsStore(
    useShallow((s) => ({
      apiKeys: s.apiKeys, llmProvider: s.llmProvider, llmModel: s.llmModel, sttProvider: s.sttProvider,
      soundEnabled: s.soundEnabled, soundVolume: s.soundVolume, routingMode: s.routingMode,
      setApiKey: s.setApiKey, setLLMProvider: s.setLLMProvider, setLLMModel: s.setLLMModel, setSTTProvider: s.setSTTProvider,
      setSoundEnabled: s.setSoundEnabled, setSoundVolume: s.setSoundVolume, setRoutingMode: s.setRoutingMode,
    }))
  );
  const { play } = useSound();
  const navigate = useNavigate();
  const addToast = useUIStore((s) => s.addToast);

  // Локальное состояние ключей для формы
  const [keyValues, setKeyValues] = useState<APIKeys>({ ...apiKeys });
  const [savingKeys, setSavingKeys] = useState(false);

  // Синхронизация при загрузке ключей из Stronghold/sessionStorage
  useEffect(() => {
    const hasStoreKeys = Object.values(apiKeys).some((v) => v.length > 0);
    const hasLocalKeys = Object.values(keyValues).some((v) => v.length > 0);
    if (hasStoreKeys && !hasLocalKeys) {
      setKeyValues({ ...apiKeys });
    }
  }, [apiKeys]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateKeyValue = (field: keyof APIKeys, value: string) => {
    setKeyValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveKeys = async () => {
    setSavingKeys(true);
    try {
      const fields = PROVIDER_KEY_FIELDS.map((p) => p.field);
      const results = await Promise.allSettled(
        fields.map((field) => setApiKey(field, keyValues[field])),
      );
      const failed = results.filter((r) => r.status === 'rejected');
      if (failed.length > 0) {
        play('error');
        const reason = (failed[0] as PromiseRejectedResult).reason;
        addToast('error', `Ошибка сохранения: ${reason instanceof Error ? reason.message : 'Хранилище недоступно'}`);
      } else {
        play('success');
        addToast('success', 'Ключи сохранены');
      }
    } catch (err) {
      play('error');
      addToast('error', `Ошибка сохранения: ${err instanceof Error ? err.message : 'Неизвестная ошибка'}`);
    } finally {
      setSavingKeys(false);
    }
  };

  // Количество настроенных ключей — считаем по обоим источникам (store + форма)
  const configuredKeysCount = PROVIDER_KEY_FIELDS.filter((p) => {
    const storeVal = apiKeys[p.field];
    const formVal = keyValues[p.field];
    return (storeVal?.length > 0) || (formVal?.length > 0);
  }).length;

  return (
    <AnimatedPage>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-text mb-6">Настройки</h1>

        {/* Routing Mode */}
        <GlassCard className="mb-5">
          <h2 className="text-lg font-semibold text-text mb-3">Режим маршрутизации</h2>
          <div className="grid grid-cols-2 gap-3">
            {([
              {
                mode: 'auto' as ProviderRoutingMode,
                title: 'Auto-routing',
                desc: configuredKeysCount > 0
                  ? `Параллельная генерация через ${configuredKeysCount} провайдеров. Автоматический fallback при rate limit.`
                  : 'Добавьте API-ключи ниже для параллельной генерации с автоматическим fallback.',
                badge: 'Рекомендуется',
              },
              {
                mode: 'single' as ProviderRoutingMode,
                title: 'Один провайдер',
                desc: 'Все запросы через один выбранный провайдер.',
                badge: '',
              },
            ]).map((opt) => {
              const isActive = routingMode === opt.mode;
              return (
                <div
                  key={opt.mode}
                  className="cursor-pointer glass-card p-3"
                  style={{
                    border: isActive ? '1.5px solid var(--accent)' : undefined,
                    boxShadow: isActive ? '0 0 0 3px var(--accent-ring), var(--shadow-card)' : undefined,
                    transition: 'all 150ms ease',
                  }}
                  onClick={() => { play('click'); setRoutingMode(opt.mode); }}
                >
                  <div className="flex items-start justify-between mb-1">
                    <p className="font-medium text-text text-sm">{opt.title}</p>
                    {opt.badge && (
                      <span className="text-[11px] font-medium px-1.5 py-0.5 rounded-full bg-primary/20 text-primary">
                        {opt.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-secondary">{opt.desc}</p>
                </div>
              );
            })}
          </div>
          {routingMode === 'auto' && configuredKeysCount < 2 && (
            <p className="text-xs font-medium text-amber-600 mt-3">
              {configuredKeysCount === 0
                ? 'Добавьте API-ключи в разделе ниже для активации auto-routing.'
                : `Для auto-routing рекомендуется минимум 2 провайдера. Настроено: ${configuredKeysCount}.`
              }
            </p>
          )}
        </GlassCard>

        {/* LLM Provider */}
        <GlassCard className="mb-5">
          <h2 className="text-lg font-semibold text-text mb-2">
            {routingMode === 'auto' ? 'Предпочтительный провайдер' : 'Провайдер ИИ (генерация)'}
          </h2>
          {routingMode === 'auto' && (
            <p className="text-xs text-text-secondary mb-3">
              В режиме auto-routing этот провайдер получает приоритет. Остальные подключаются автоматически.
            </p>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {LLM_PROVIDER_INFO.map((info) => {
              const isActive = llmProvider === info.id;
              return (
                <div
                  key={info.id}
                  className="cursor-pointer glass-card p-3"
                  style={{
                    border: isActive ? '1.5px solid var(--accent)' : undefined,
                    boxShadow: isActive ? '0 0 0 3px var(--accent-ring), var(--shadow-card)' : undefined,
                    transition: 'all 150ms ease',
                  }}
                  onClick={() => { play('click'); setLLMProvider(info.id); }}
                >
                  <div className="flex items-start justify-between mb-1">
                    <p className="font-medium text-text text-sm">{info.name}</p>
                    <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded-full ${
                      info.badge === 'Бесплатно' ? 'bg-green-600/20 text-green-700' :
                      info.badge === '~Бесплатно' ? 'bg-amber-600/20 text-amber-700' :
                      'bg-text-muted/20 text-text-secondary'
                    }`}>
                      {info.badge}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary font-medium">{info.model}</p>
                  <p className="text-xs text-text-muted mt-0.5">{info.desc}</p>
                </div>
              );
            })}
          </div>

          {/* Model selector */}
          {PROVIDER_MODELS[llmProvider]?.length > 0 && (
            <div className="mt-4">
              <label className="text-sm text-text-secondary mb-2 block">
                Модель: {llmModel || DEFAULT_LLM_MODELS[llmProvider]}
              </label>
              <div className="grid grid-cols-2 gap-2">
                {PROVIDER_MODELS[llmProvider].map((m) => {
                  const isActive = (llmModel || DEFAULT_LLM_MODELS[llmProvider]) === m.id;
                  return (
                    <button
                      key={m.id}
                      onClick={() => { play('click'); setLLMModel(m.id === DEFAULT_LLM_MODELS[llmProvider] ? '' : m.id); }}
                      className={`text-left px-3 py-2 rounded-lg text-sm transition-all ${
                        isActive
                          ? 'bg-primary/15 text-primary font-medium ring-1 ring-primary/30'
                          : 'bg-white/5 text-text-secondary hover:bg-white/10'
                      }`}
                    >
                      {m.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </GlassCard>

        {/* STT Provider */}
        <GlassCard className="mb-5">
          <h2 className="text-lg font-semibold text-text mb-4">Транскрипция (STT)</h2>
          <div className="grid grid-cols-2 gap-3">
            {STT_PROVIDER_INFO.map((info) => {
              const isActive = sttProvider === info.id;
              return (
                <div
                  key={info.id}
                  className="cursor-pointer glass-card p-3"
                  style={{
                    border: isActive ? '1.5px solid var(--accent)' : undefined,
                    boxShadow: isActive ? '0 0 0 3px var(--accent-ring), var(--shadow-card)' : undefined,
                    transition: 'all 150ms ease',
                  }}
                  onClick={() => { play('click'); setSTTProvider(info.id); }}
                >
                  <div className="flex items-start justify-between mb-1">
                    <p className="font-medium text-text text-sm">{info.name}</p>
                    <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded-full ${
                      info.badge === 'Бесплатно' ? 'bg-green-600/20 text-green-700' :
                      'bg-text-muted/20 text-text-secondary'
                    }`}>
                      {info.badge}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary font-medium">{info.model}</p>
                  <p className="text-xs text-text-muted mt-0.5">{info.desc}</p>
                </div>
              );
            })}
          </div>
        </GlassCard>

        {/* API Keys */}
        <GlassCard className="mb-5">
          <h2 className="text-lg font-semibold text-text mb-2">API-ключи</h2>
          <p className="text-xs text-text-secondary mb-4">
            {routingMode === 'auto'
              ? `Чем больше ключей — тем быстрее обработка и больше запас лимитов. Настроено: ${configuredKeysCount}/${PROVIDER_KEY_FIELDS.length}`
              : 'Укажите ключ для выбранного провайдера. Ключи шифруются через Stronghold.'
            }
          </p>
          <div className="flex flex-col gap-3">
            {PROVIDER_KEY_FIELDS.map((p) => (
              <div key={p.field}>
                <GlassInput
                  label={p.label}
                  type="password"
                  placeholder={p.placeholder}
                  value={keyValues[p.field]}
                  onChange={(e) => updateKeyValue(p.field, e.target.value)}
                />
                {p.hint && (
                  <p className="text-[11px] text-text-muted mt-0.5 ml-1">{p.hint}</p>
                )}
              </div>
            ))}
            <GlassButton variant="primary" size="sm" onClick={handleSaveKeys} loading={savingKeys}>
              Сохранить ключи
            </GlassButton>
          </div>
        </GlassCard>

        {/* Sound */}
        <GlassCard className="mb-5">
          <h2 className="text-lg font-semibold text-text mb-4">Звук</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text">Звуковые эффекты</p>
              <p className="text-xs text-text-secondary">Звуки при навигации и действиях</p>
            </div>
            <button
              onClick={() => { setSoundEnabled(!soundEnabled); play('click'); }}
              className={`
                w-12 h-7 rounded-full transition-colors duration-200 relative
                ${soundEnabled ? 'bg-primary' : 'bg-text-muted/30'}
              `}
            >
              <div
                className={`
                  absolute top-1 w-5 h-5 rounded-full bg-white shadow-sm
                  transition-transform duration-200
                  ${soundEnabled ? 'left-6' : 'left-1'}
                `}
              />
            </button>
          </div>

          {soundEnabled && (
            <div className="mt-4">
              <label className="text-sm text-text-secondary mb-2 block">
                Громкость: {Math.round(soundVolume * 100)}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={soundVolume * 100}
                onChange={(e) => setSoundVolume(Number(e.target.value) / 100)}
                className="w-full accent-primary"
              />
            </div>
          )}
        </GlassCard>

        {/* About */}
        <GlassCard variant="subtle">
          <h2 className="text-lg font-semibold text-text mb-3">О программе</h2>
          <p className="text-sm text-text-secondary mb-4">
            Aether v0.1.0 — превращение записей встреч в структурированные документы
          </p>
          <div className="flex flex-col gap-2">
            <button
              onClick={() => navigate('/guide')}
              className="flex items-center gap-2 text-sm text-primary font-medium hover:text-primary/80 transition-colors text-left"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.2" />
                <path d="M6.5 6C6.5 5.17 7.17 4.5 8 4.5C8.83 4.5 9.5 5.17 9.5 6C9.5 6.83 8.83 7.5 8 7.5V8.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                <circle cx="8" cy="10.5" r="0.6" fill="currentColor" />
              </svg>
              Справка и руководство
            </button>
          </div>
        </GlassCard>
      </div>
    </AnimatedPage>
  );
}
