/**
 * Индикатор этапа пайплайна.
 * Анимированный, с цветовой индикацией статуса.
 */

import { motion } from 'motion/react';
import type { StageStatus } from '@/types/pipeline.types';

interface StageIndicatorProps {
  status: StageStatus;
  index: number;
}

const statusStyles: Record<StageStatus, { bg: string; text: string; ring: string }> = {
  pending: { bg: 'bg-text-muted/10', text: 'text-text-muted', ring: '' },
  active: { bg: 'bg-primary/15', text: 'text-primary', ring: 'ring-2 ring-primary/30' },
  completed: { bg: 'bg-success/15', text: 'text-success', ring: '' },
  error: { bg: 'bg-error/15', text: 'text-error', ring: 'ring-2 ring-error/30' },
};

export function StageIndicator({ status, index }: StageIndicatorProps) {
  const style = statusStyles[status];

  return (
    <div className={`relative w-11 h-11 rounded-xl flex items-center justify-center ${style.bg} ${style.ring} ${style.text}`}>
      {status === 'completed' && (
        <motion.svg
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        >
          <motion.path
            d="M4 10L8.5 14.5L16 5.5"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          />
        </motion.svg>
      )}

      {status === 'active' && (
        <>
          {/* Пульсирующий фон */}
          <motion.div
            className="absolute inset-0 rounded-xl bg-primary/10"
            animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
          {/* Спиннер */}
          <motion.div
            className="w-5 h-5 border-2 border-current border-t-transparent rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
          />
        </>
      )}

      {status === 'error' && (
        <motion.svg
          width="18"
          height="18"
          viewBox="0 0 18 18"
          fill="none"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 15 }}
        >
          <path d="M5 5L13 13M5 13L13 5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </motion.svg>
      )}

      {status === 'pending' && (
        <span className="text-xs font-bold opacity-60">{index + 1}</span>
      )}
    </div>
  );
}
