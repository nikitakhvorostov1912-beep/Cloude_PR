/**
 * Карточка прогресса артефакта в пайплайне.
 * Показывает статус генерации каждого артефакта.
 */

import { motion } from 'motion/react';
import { ARTIFACT_LABELS, ARTIFACT_ICONS } from '@/types/artifact.types';
import type { ArtifactType } from '@/types/artifact.types';

export type ArtifactStatus = 'pending' | 'generating' | 'completed' | 'empty' | 'error';

interface ArtifactProgressItem {
  type: ArtifactType;
  status: ArtifactStatus;
  error?: string;
}

interface ArtifactProgressProps {
  items: ArtifactProgressItem[];
}

const statusConfig: Record<ArtifactStatus, { bg: string; text: string; label: string }> = {
  pending: { bg: 'bg-text-muted/10', text: 'text-text-muted', label: 'Ожидание' },
  generating: { bg: 'bg-primary/10', text: 'text-primary', label: 'Генерация...' },
  completed: { bg: 'bg-success/10', text: 'text-success', label: 'Готово' },
  empty: { bg: 'bg-warning/10', text: 'text-warning', label: 'Пусто' },
  error: { bg: 'bg-error/10', text: 'text-error', label: 'Ошибка' },
};

export function ArtifactProgress({ items }: ArtifactProgressProps) {
  if (items.length === 0) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {items.map((item, i) => {
        const config = statusConfig[item.status];
        return (
          <motion.div
            key={item.type}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            className={`rounded-xl p-3 ${config.bg} transition-colors duration-300`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-base">{ARTIFACT_ICONS[item.type]}</span>
              <span className={`text-xs font-medium ${config.text}`}>
                {ARTIFACT_LABELS[item.type]}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              {item.status === 'generating' && (
                <motion.div
                  className="w-2 h-2 rounded-full bg-primary"
                  animate={{ scale: [1, 1.4, 1], opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              )}
              {item.status === 'completed' && (
                <motion.svg
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="none"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                >
                  <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </motion.svg>
              )}
              {item.status === 'error' && (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 3L9 9M3 9L9 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              )}

              <span className={`text-[10px] ${config.text} opacity-80`}>
                {item.error ? item.error.slice(0, 30) : config.label}
              </span>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
