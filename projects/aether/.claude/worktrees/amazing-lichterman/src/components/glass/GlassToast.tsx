import { motion, AnimatePresence } from 'motion/react';
import { useUIStore } from '@/stores/ui.store';

const typeStyles = {
  success: 'border-l-4 border-l-success',
  error: 'border-l-4 border-l-error',
  warning: 'border-l-4 border-l-warning',
  info: 'border-l-4 border-l-primary',
};

const typeIcons = {
  success: (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-success">
      <circle cx="9" cy="9" r="8" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5.5 9L8 11.5L12.5 6.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  error: (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-error">
      <circle cx="9" cy="9" r="8" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6 6L12 12M6 12L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  warning: (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-warning">
      <path d="M9 2L16.5 15.5H1.5L9 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M9 7V10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="9" cy="13" r="0.75" fill="currentColor" />
    </svg>
  ),
  info: (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-primary">
      <circle cx="9" cy="9" r="8" stroke="currentColor" strokeWidth="1.5" />
      <path d="M9 8V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="9" cy="5.5" r="0.75" fill="currentColor" />
    </svg>
  ),
};

export function GlassToastContainer() {
  const toasts = useUIStore((s) => s.toasts);
  const removeToast = useUIStore((s) => s.removeToast);

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, x: 80, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 80, scale: 0.9 }}
            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
            className={`glass-strong p-4 flex gap-3 items-start cursor-pointer ${typeStyles[toast.type]}`}
            onClick={() => removeToast(toast.id)}
          >
            <span className="flex-shrink-0 mt-0.5">{typeIcons[toast.type]}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text">{toast.title}</p>
              {toast.description && (
                <p className="text-xs text-text-secondary mt-0.5">{toast.description}</p>
              )}
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
