import { useState } from 'react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton, GlassInput } from '@/components/glass';
import { useSettingsStore } from '@/stores/settings.store';
import { useShallow } from 'zustand/react/shallow';
import { useSound } from '@/hooks/useSound';

export function SettingsPage() {
  const { apiKeys, llmProvider, soundEnabled, soundVolume, setApiKey, setLLMProvider, setSoundEnabled, setSoundVolume } = useSettingsStore(
    useShallow((s) => ({
      apiKeys: s.apiKeys, llmProvider: s.llmProvider, soundEnabled: s.soundEnabled, soundVolume: s.soundVolume,
      setApiKey: s.setApiKey, setLLMProvider: s.setLLMProvider, setSoundEnabled: s.setSoundEnabled, setSoundVolume: s.setSoundVolume,
    }))
  );
  const { play } = useSound();
  const [openaiKey, setOpenaiKey] = useState(apiKeys.openaiKey);
  const [claudeKey, setClaudeKey] = useState(apiKeys.claudeKey);

  const handleSaveKeys = () => {
    setApiKey('openaiKey', openaiKey);
    setApiKey('claudeKey', claudeKey);
    play('success');
  };

  return (
    <AnimatedPage>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-text mb-6">Настройки</h1>

        {/* API Keys */}
        <GlassCard className="mb-5">
          <h2 className="text-lg font-semibold text-text mb-4">API-ключи</h2>
          <div className="flex flex-col gap-4">
            <GlassInput
              label="OpenAI API Key"
              type="password"
              placeholder="sk-..."
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
            />
            <GlassInput
              label="Claude API Key"
              type="password"
              placeholder="sk-ant-..."
              value={claudeKey}
              onChange={(e) => setClaudeKey(e.target.value)}
            />
            <GlassButton variant="primary" size="sm" onClick={handleSaveKeys}>
              Сохранить ключи
            </GlassButton>
          </div>
        </GlassCard>

        {/* AI Provider */}
        <GlassCard className="mb-5">
          <h2 className="text-lg font-semibold text-text mb-4">Предпочтительный AI</h2>
          <div className="flex gap-3">
            {(['claude', 'openai'] as const).map((provider) => (
              <GlassCard
                key={provider}
                variant={llmProvider === provider ? 'strong' : 'subtle'}
                hoverable
                padding="sm"
                className={`flex-1 text-center cursor-pointer ${
                  llmProvider === provider ? 'ring-2 ring-primary/30' : ''
                }`}
                onClick={() => {
                  play('click');
                  setLLMProvider(provider);
                }}
              >
                <p className="font-medium text-text">
                  {provider === 'claude' ? 'Claude' : 'OpenAI GPT-4'}
                </p>
                <p className="text-xs text-text-secondary mt-1">
                  {provider === 'claude' ? 'Anthropic Sonnet 4.6' : 'OpenAI GPT-4'}
                </p>
              </GlassCard>
            ))}
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
              onClick={() => {
                setSoundEnabled(!soundEnabled);
                play('click');
              }}
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
          <h2 className="text-lg font-semibold text-text mb-2">О программе</h2>
          <p className="text-sm text-text-secondary">
            Aether v0.1.0 — превращение записей встреч в структурированные документы
          </p>
        </GlassCard>
      </div>
    </AnimatedPage>
  );
}
