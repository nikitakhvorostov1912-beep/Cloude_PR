/**
 * Табы для переключения между типами артефактов.
 * Glass-стиль с анимированным индикатором.
 */

import { motion } from 'motion/react';
import { ARTIFACT_LABELS, ARTIFACT_ICONS } from '@/types/artifact.types';
import type { ArtifactType } from '@/types/artifact.types';

interface ArtifactTabsProps {
  types: ArtifactType[];
  activeType: ArtifactType;
  onSelect: (type: ArtifactType) => void;
  hasError?: (type: ArtifactType) => boolean;
  isEmpty?: (type: ArtifactType) => boolean;
}

export function ArtifactTabs({ types, activeType, onSelect, hasError, isEmpty }: ArtifactTabsProps) {
  return (
    <div className="flex gap-1 p-1 rounded-xl glass-subtle overflow-x-auto">
      {types.map((type) => {
        const isActive = type === activeType;
        const isError = hasError?.(type);
        const isEmptyArt = isEmpty?.(type);

        return (
          <button
            key={type}
            onClick={() => onSelect(type)}
            className={`relative flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              isActive
                ? 'text-primary'
                : isError
                  ? 'text-error/70 hover:text-error'
                  : isEmptyArt
                    ? 'text-text-muted hover:text-text-secondary'
                    : 'text-text-secondary hover:text-text'
            }`}
          >
            {isActive && (
              <motion.div
                layoutId="artifact-tab-indicator"
                className="absolute inset-0 bg-white/80 rounded-lg shadow-sm"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative z-10 text-base">{ARTIFACT_ICONS[type]}</span>
            <span className="relative z-10">{ARTIFACT_LABELS[type]}</span>
            {isError && (
              <span className="relative z-10 w-1.5 h-1.5 rounded-full bg-error" />
            )}
          </button>
        );
      })}
    </div>
  );
}
