import { motion } from 'motion/react';
import type { FileInfo } from '@/services/file.service';
import { formatDuration } from '@/services/file.service';

interface FileCardProps {
  file: FileInfo;
  onRemove?: () => void;
}

const FILE_TYPE_ICONS = {
  audio: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 2V14M6 10V14M14 6V14M2 10V14M18 8V14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  video: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="2" y="4" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="2" />
      <path d="M14 8L18 5V15L14 12" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  ),
  unknown: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M4 2H12L16 6V18H4V2Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  ),
};

export function FileCard({ file, onRemove }: FileCardProps) {
  return (
    <motion.div
      className="glass-subtle rounded-xl p-4 flex items-center gap-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary flex-shrink-0">
        {FILE_TYPE_ICONS[file.type]}
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text truncate">{file.name}</p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-xs text-text-secondary">{file.sizeFormatted}</span>
          <span className="text-xs text-text-muted">·</span>
          <span className="text-xs text-text-secondary">{formatDuration(file.durationSeconds)}</span>
          <span className="text-xs text-text-muted">·</span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium uppercase">
            {file.extension}
          </span>
        </div>
      </div>

      {onRemove && (
        <motion.button
          className="w-8 h-8 rounded-lg flex items-center justify-center text-text-muted hover:text-error hover:bg-error/10 transition-colors flex-shrink-0"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={onRemove}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 3L11 11M3 11L11 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </motion.button>
      )}
    </motion.div>
  );
}
