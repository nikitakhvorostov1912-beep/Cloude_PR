/**
 * Компонент стриминга текста.
 * Показывает промежуточные результаты обработки с мигающим курсором.
 */

import { useRef, useEffect } from 'react';
import { motion } from 'motion/react';
import { GlassCard } from '@/components/glass';

interface StreamingTextProps {
  text: string;
  isActive: boolean;
  maxHeight?: number;
}

export function StreamingText({ text, isActive, maxHeight = 280 }: StreamingTextProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Автоскролл вниз при новом тексте
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [text]);

  if (!text) return null;

  return (
    <GlassCard variant="subtle" padding="md">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text">Лог обработки</h3>
        {isActive && (
          <div className="flex items-center gap-1.5">
            <motion.div
              className="w-1.5 h-1.5 rounded-full bg-primary"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <span className="text-xs text-primary font-medium">Обработка...</span>
          </div>
        )}
      </div>

      <div
        ref={containerRef}
        className="font-mono text-xs text-text-secondary whitespace-pre-wrap overflow-y-auto rounded-lg bg-surface/30 p-3"
        style={{ maxHeight }}
      >
        {text}
        {isActive && (
          <motion.span
            className="inline-block w-1.5 h-4 bg-primary ml-0.5 align-text-bottom"
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.6, repeat: Infinity }}
          />
        )}
      </div>
    </GlassCard>
  );
}
