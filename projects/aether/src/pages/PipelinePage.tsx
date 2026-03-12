import { motion } from 'motion/react';
import { AnimatedPage } from '@/components/shared/AnimatedPage';
import { GlassCard } from '@/components/glass';
import { EmptyState } from '@/components/shared/EmptyState';
import { usePipelineStore } from '@/stores/pipeline.store';
import { useShallow } from 'zustand/react/shallow';
import { STAGE_LABELS, STAGE_DESCRIPTIONS } from '@/types/pipeline.types';
import type { PipelineStage, StageStatus } from '@/types/pipeline.types';

const stageOrder: PipelineStage[] = ['upload', 'extract', 'transcribe', 'generate', 'complete'];

const statusColors: Record<StageStatus, string> = {
  pending: 'bg-text-muted/20 text-text-muted',
  active: 'bg-primary/20 text-primary',
  completed: 'bg-success/20 text-success',
  error: 'bg-error/20 text-error',
};

export function PipelinePage() {
  const { meetingId, stages, streamingText, progress, error } = usePipelineStore(
    useShallow((s) => ({ meetingId: s.meetingId, stages: s.stages, streamingText: s.streamingText, progress: s.progress, error: s.error }))
  );

  if (!meetingId) {
    return (
      <AnimatedPage>
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold text-text mb-6">Обработка</h1>
          <EmptyState
            title="Нет активной обработки"
            description="Загрузите файл на главной странице для начала обработки"
            icon={
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="2" />
                <path d="M12 16L15 19L20 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            }
          />
        </div>
      </AnimatedPage>
    );
  }

  return (
    <AnimatedPage>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-text mb-2">Обработка</h1>
        <p className="text-sm text-text-secondary mb-8">
          Прогресс: {Math.round(progress)}%
        </p>

        {/* Progress bar */}
        <div className="h-1.5 rounded-full bg-primary/10 mb-8 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-primary to-secondary"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Stages */}
        <div className="flex flex-col gap-4 mb-8">
          {stageOrder.map((stage, i) => (
            <motion.div
              key={stage}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <GlassCard
                variant={stages[stage] === 'active' ? 'strong' : 'subtle'}
                padding="md"
                className={stages[stage] === 'active' ? 'ring-2 ring-primary/30' : ''}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${statusColors[stages[stage]]}`}>
                    {stages[stage] === 'completed' ? (
                      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                        <path d="M4 9L8 13L14 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : stages[stage] === 'active' ? (
                      <motion.div
                        className="w-4 h-4 border-2 border-current border-t-transparent rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                      />
                    ) : stages[stage] === 'error' ? (
                      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                        <path d="M5 5L13 13M5 13L13 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    ) : (
                      <span className="text-xs font-bold">{i + 1}</span>
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-text">{STAGE_LABELS[stage]}</p>
                    <p className="text-xs text-text-secondary">{STAGE_DESCRIPTIONS[stage]}</p>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>

        {/* Streaming text */}
        {streamingText && (
          <GlassCard variant="subtle" padding="md">
            <h3 className="text-sm font-semibold text-text mb-3">Промежуточные результаты</h3>
            <div className="font-mono text-xs text-text-secondary whitespace-pre-wrap max-h-48 overflow-y-auto">
              {streamingText}
              <motion.span
                className="inline-block w-1.5 h-4 bg-primary ml-0.5"
                animate={{ opacity: [1, 0] }}
                transition={{ duration: 0.5, repeat: Infinity }}
              />
            </div>
          </GlassCard>
        )}

        {/* Error */}
        {error && (
          <GlassCard variant="subtle" padding="md" className="border-error/30 mt-4">
            <p className="text-sm text-error font-medium mb-1">Ошибка обработки</p>
            <p className="text-xs text-text-secondary">{error}</p>
          </GlassCard>
        )}
      </div>
    </AnimatedPage>
  );
}
