import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton, GlassInput } from '@/components/glass';
import { useSettingsStore } from '@/stores/settings.store';
import { useShallow } from 'zustand/react/shallow';
import { useSound } from '@/hooks/useSound';

const isTauri = (): boolean => '__TAURI_INTERNALS__' in window;

const STEPS = [
  { title: 'Добро пожаловать в Aether', subtitle: 'Превращайте записи встреч в структурированные документы' },
  { title: 'Настройте API-ключи', subtitle: 'Подключите OpenAI и Claude для обработки' },
  { title: 'Всё готово!', subtitle: 'Создайте первый проект и загрузите запись' },
];

export function OnboardingPage() {
  const [step, setStep] = useState(0);
  const navigate = useNavigate();
  const { play } = useSound();
  const { apiKeys, setApiKey, setOnboardingCompleted } = useSettingsStore(
    useShallow((s) => ({ apiKeys: s.apiKeys, setApiKey: s.setApiKey, setOnboardingCompleted: s.setOnboardingCompleted }))
  );
  const [openaiKey, setOpenaiKey] = useState(apiKeys.openaiKey);
  const [claudeKey, setClaudeKey] = useState(apiKeys.claudeKey);
  const [verifyingOpenai, setVerifyingOpenai] = useState(false);
  const [verifyingClaude, setVerifyingClaude] = useState(false);
  const [openaiValid, setOpenaiValid] = useState<boolean | null>(null);
  const [claudeValid, setClaudeValid] = useState<boolean | null>(null);

  const canProceedStep1 = openaiKey.length > 10 || claudeKey.length > 10;

  const handleNext = () => {
    play('navigate');
    if (step === 1) {
      if (openaiKey) setApiKey('openaiKey', openaiKey);
      if (claudeKey) setApiKey('claudeKey', claudeKey);
    }
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    play('click');
    if (step > 0) setStep(step - 1);
  };

  const handleFinish = () => {
    play('success');
    setOnboardingCompleted(true);
    navigate('/');
  };

  const verifyOpenai = async () => {
    setVerifyingOpenai(true);
    try {
      let valid = false;
      if (isTauri()) {
        const { invoke } = await import('@tauri-apps/api/core');
        valid = await invoke<boolean>('validate_openai_key', { apiKey: openaiKey });
      } else {
        const res = await fetch('https://api.openai.com/v1/models', {
          headers: { Authorization: `Bearer ${openaiKey}` },
        });
        valid = res.ok;
      }
      setOpenaiValid(valid);
      play(valid ? 'success' : 'error');
    } catch {
      setOpenaiValid(false);
      play('error');
    }
    setVerifyingOpenai(false);
  };

  const verifyClaude = async () => {
    setVerifyingClaude(true);
    try {
      let valid = false;
      if (isTauri()) {
        const { invoke } = await import('@tauri-apps/api/core');
        valid = await invoke<boolean>('validate_claude_key', { apiKey: claudeKey });
      } else {
        const res = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'x-api-key': claudeKey,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
          },
          body: JSON.stringify({
            model: 'claude-sonnet-4-6',
            max_tokens: 1,
            messages: [{ role: 'user', content: 'hi' }],
          }),
        });
        valid = res.status !== 401 && res.status !== 403;
      }
      setClaudeValid(valid);
      play(valid ? 'success' : 'error');
    } catch {
      setClaudeValid(false);
      play('error');
    }
    setVerifyingClaude(false);
  };

  return (
    <AnimatedPage className="flex items-center justify-center">
      <div className="w-full max-w-xl">
        {/* Progress dots */}
        <div className="flex justify-center gap-2 mb-8">
          {STEPS.map((_, i) => (
            <motion.div
              key={i}
              className={`h-2 rounded-full ${i === step ? 'bg-primary' : 'bg-primary/20'}`}
              animate={{ width: i === step ? 32 : 8 }}
              transition={{ type: 'spring', damping: 20, stiffness: 300 }}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.3 }}
          >
            <GlassCard variant="strong" padding="lg" className="text-center">
              {/* Step 0: Welcome */}
              {step === 0 && (
                <div className="flex flex-col items-center gap-6">
                  <motion.div
                    className="w-20 h-20 rounded-3xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', damping: 15, stiffness: 200, delay: 0.2 }}
                  >
                    <span className="text-white text-3xl font-bold">AE</span>
                  </motion.div>
                  <div>
                    <motion.h1
                      className="text-2xl font-bold text-text mb-2"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                    >
                      {STEPS[0].title}
                    </motion.h1>
                    <motion.p
                      className="text-text-secondary"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 }}
                    >
                      {STEPS[0].subtitle}
                    </motion.p>
                  </div>
                  <motion.div
                    className="flex flex-col gap-3 w-full max-w-xs text-left"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                  >
                    {[
                      'Загрузите аудио или видео встречи',
                      'AI создаст протокол, ТЗ, карту рисков',
                      'Экспортируйте в DOCX или PDF',
                    ].map((text, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                          <span className="text-primary text-xs font-bold">{i + 1}</span>
                        </div>
                        <span className="text-sm text-text-secondary">{text}</span>
                      </div>
                    ))}
                  </motion.div>
                </div>
              )}

              {/* Step 1: API Keys */}
              {step === 1 && (
                <div className="flex flex-col gap-5 text-left">
                  <div className="text-center mb-2">
                    <h2 className="text-xl font-bold text-text">{STEPS[1].title}</h2>
                    <p className="text-sm text-text-secondary mt-1">{STEPS[1].subtitle}</p>
                  </div>

                  <GlassCard variant="subtle" padding="md">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-text">OpenAI API Key</span>
                      {openaiValid === true && <span className="text-xs text-success font-medium">Подключён</span>}
                      {openaiValid === false && <span className="text-xs text-error font-medium">Ошибка</span>}
                    </div>
                    <div className="flex gap-2">
                      <GlassInput
                        type="password"
                        placeholder="sk-..."
                        value={openaiKey}
                        onChange={(e) => {
                          setOpenaiKey(e.target.value);
                          setOpenaiValid(null);
                        }}
                        className="flex-1"
                      />
                      <GlassButton
                        variant="secondary"
                        size="sm"
                        loading={verifyingOpenai}
                        disabled={openaiKey.length < 10}
                        onClick={verifyOpenai}
                      >
                        Проверить
                      </GlassButton>
                    </div>
                    <p className="text-xs text-text-muted mt-2">Для Whisper (транскрипция) и GPT-4</p>
                  </GlassCard>

                  <GlassCard variant="subtle" padding="md">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-text">Claude API Key</span>
                      {claudeValid === true && <span className="text-xs text-success font-medium">Подключён</span>}
                      {claudeValid === false && <span className="text-xs text-error font-medium">Ошибка</span>}
                    </div>
                    <div className="flex gap-2">
                      <GlassInput
                        type="password"
                        placeholder="sk-ant-..."
                        value={claudeKey}
                        onChange={(e) => {
                          setClaudeKey(e.target.value);
                          setClaudeValid(null);
                        }}
                        className="flex-1"
                      />
                      <GlassButton
                        variant="secondary"
                        size="sm"
                        loading={verifyingClaude}
                        disabled={claudeKey.length < 10}
                        onClick={verifyClaude}
                      >
                        Проверить
                      </GlassButton>
                    </div>
                    <p className="text-xs text-text-muted mt-2">Для генерации артефактов</p>
                  </GlassCard>

                  <p className="text-xs text-text-muted text-center">
                    Достаточно подключить хотя бы один. Второй можно добавить позже.
                  </p>
                </div>
              )}

              {/* Step 2: Ready */}
              {step === 2 && (
                <div className="flex flex-col items-center gap-6">
                  <motion.div
                    className="w-16 h-16 rounded-2xl bg-success/10 flex items-center justify-center"
                    initial={{ scale: 0, rotate: -180 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: 'spring', damping: 15, stiffness: 200 }}
                  >
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="text-success">
                      <path d="M8 16L14 22L24 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </motion.div>
                  <div>
                    <h2 className="text-xl font-bold text-text">{STEPS[2].title}</h2>
                    <p className="text-sm text-text-secondary mt-1">{STEPS[2].subtitle}</p>
                  </div>
                </div>
              )}

              {/* Navigation */}
              <div className="flex justify-between items-center mt-8 pt-5 border-t border-white/20">
                <div>
                  {step > 0 && (
                    <GlassButton variant="ghost" onClick={handleBack}>
                      Назад
                    </GlassButton>
                  )}
                </div>
                <div>
                  {step < STEPS.length - 1 ? (
                    <GlassButton
                      onClick={handleNext}
                      disabled={step === 1 && !canProceedStep1}
                    >
                      Далее
                    </GlassButton>
                  ) : (
                    <GlassButton onClick={handleFinish}>
                      Начать работу
                    </GlassButton>
                  )}
                </div>
              </div>
            </GlassCard>
          </motion.div>
        </AnimatePresence>
      </div>
    </AnimatedPage>
  );
}
