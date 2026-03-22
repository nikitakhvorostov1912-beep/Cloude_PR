import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard, GlassButton, GlassInput } from '@/components/glass';
import { useSettingsStore } from '@/stores/settings.store';
import { useShallow } from 'zustand/react/shallow';
import { useSound } from '@/hooks/useSound';
import { KEY_PATTERNS } from '@/lib/constants';

const STEPS = [
  { title: 'Добро пожаловать в Aether', subtitle: 'Превращайте записи встреч в структурированные документы' },
  { title: 'Бесплатный старт', subtitle: 'Groq — бесплатная транскрипция и генерация артефактов' },
  { title: 'Всё готово!', subtitle: 'Создайте первый проект и загрузите запись' },
];

export function OnboardingPage() {
  const [step, setStep] = useState(0);
  const navigate = useNavigate();
  const { play } = useSound();
  const { apiKeys, setApiKey, setOnboardingCompleted, setLLMProvider, setSTTProvider } = useSettingsStore(
    useShallow((s) => ({
      apiKeys: s.apiKeys, setApiKey: s.setApiKey, setOnboardingCompleted: s.setOnboardingCompleted,
      setLLMProvider: s.setLLMProvider, setSTTProvider: s.setSTTProvider,
    }))
  );

  // Free-first: Groq + DeepSeek
  const [groqKey, setGroqKey] = useState(apiKeys.groqKey);
  const [deepseekKey, setDeepseekKey] = useState(apiKeys.deepseekKey);

  const isGroqValid = KEY_PATTERNS.groq.test(groqKey);
  const isDeepseekValid = KEY_PATTERNS.deepseek.test(deepseekKey);

  // Минимум для старта: Groq ключ (покрывает и STT, и LLM)
  const canProceedStep1 = isGroqValid;

  const handleNext = async () => {
    play('navigate');
    if (step === 1) {
      // Сохраняем бесплатные ключи
      if (groqKey) await setApiKey('groqKey', groqKey);
      if (deepseekKey) await setApiKey('deepseekKey', deepseekKey);
      // Устанавливаем бесплатные провайдеры
      setSTTProvider('groq');
      if (isDeepseekValid) {
        setLLMProvider('deepseek');
      } else {
        setLLMProvider('groq');
      }
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

              {/* Step 1: Free APIs — Groq + DeepSeek */}
              {step === 1 && (
                <div className="flex flex-col gap-5 text-left">
                  <div className="text-center mb-2">
                    <h2 className="text-xl font-bold text-text">{STEPS[1].title}</h2>
                    <p className="text-sm text-text-secondary mt-1">{STEPS[1].subtitle}</p>
                  </div>

                  <GlassCard variant="subtle" padding="md">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-text">Groq API Key</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-400">
                        Бесплатно
                      </span>
                    </div>
                    <GlassInput
                      type="password"
                      placeholder="gsk_..."
                      value={groqKey}
                      onChange={(e) => setGroqKey(e.target.value)}
                    />
                    <p className="text-xs text-text-muted mt-2">
                      Whisper (транскрипция) + Qwen3-32B (генерация). 8ч аудио/день, 500K токенов/день.
                    </p>
                    {groqKey && !isGroqValid && (
                      <p className="text-xs text-warning mt-1">Ключ должен начинаться с gsk_</p>
                    )}
                  </GlassCard>

                  <GlassCard variant="subtle" padding="md">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-text">DeepSeek API Key</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                        ~Бесплатно
                      </span>
                    </div>
                    <GlassInput
                      type="password"
                      placeholder="sk-..."
                      value={deepseekKey}
                      onChange={(e) => setDeepseekKey(e.target.value)}
                    />
                    <p className="text-xs text-text-muted mt-2">
                      Опционально. Лучшее качество для русского текста. 5M бонусных токенов при регистрации.
                    </p>
                  </GlassCard>

                  <p className="text-xs text-text-muted text-center">
                    Достаточно только Groq для начала работы. Другие провайдеры — в настройках.
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
                <div className="flex items-center gap-3">
                  {step === 1 && !canProceedStep1 && (
                    <p className="text-xs text-warning">Введите Groq API-ключ</p>
                  )}
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
