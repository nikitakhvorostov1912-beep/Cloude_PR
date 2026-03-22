/**
 * Визуализация этапов пайплайна.
 * Горизонтальная цепочка glass-карточек с анимацией.
 */

import { motion } from 'motion/react';
import { GlassCard } from '@/components/glass';
import { StageIndicator } from './StageIndicator';
import { STAGE_LABELS, STAGE_DESCRIPTIONS } from '@/types/pipeline.types';
import type { PipelineStage, StageStatus } from '@/types/pipeline.types';

const STAGE_ORDER: PipelineStage[] = ['upload', 'extract', 'transcribe', 'generate', 'complete'];

interface PipelineStagesProps {
  stages: Record<PipelineStage, StageStatus>;
  progress: number;
}

export function PipelineStages({ stages, progress }: PipelineStagesProps) {
  return (
    <div className="space-y-3">
      {/* Прогресс-бар */}
      <div className="relative h-1.5 rounded-full bg-surface/50 overflow-hidden">
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-primary via-secondary to-primary"
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
        {/* Shimmer-эффект */}
        {progress > 0 && progress < 100 && (
          <motion.div
            className="absolute inset-y-0 w-20 bg-gradient-to-r from-transparent via-white/30 to-transparent"
            animate={{ left: ['-5rem', '100%'] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          />
        )}
      </div>

      {/* Этапы */}
      <div className="flex flex-col gap-2">
        {STAGE_ORDER.map((stage, i) => {
          const status = stages[stage];
          const isActive = status === 'active';

          return (
            <motion.div
              key={stage}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08, duration: 0.3 }}
            >
              <GlassCard
                variant={isActive ? 'default' : 'subtle'}
                padding="sm"
                className={`transition-all duration-300 ${isActive ? 'ring-1 ring-primary/20 shadow-lg shadow-primary/5' : ''}`}
              >
                <div className="flex items-center gap-3">
                  <StageIndicator status={status} index={i} />

                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium ${isActive ? 'text-text' : status === 'completed' ? 'text-success' : status === 'error' ? 'text-error' : 'text-text-muted'}`}>
                      {STAGE_LABELS[stage]}
                    </p>
                    <p className="text-xs text-text-secondary truncate">
                      {STAGE_DESCRIPTIONS[stage]}
                    </p>
                  </div>

                  {/* Линия соединения */}
                  {i < STAGE_ORDER.length - 1 && (
                    <div className="hidden" /> // Вертикальная линия между карточками реализована через gap
                  )}
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
