import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';

interface GlassInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: ReactNode;
}

export const GlassInput = forwardRef<HTMLInputElement, GlassInputProps>(
  ({ label, error, icon, className = '', ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-muted)' }}>
              {icon}
            </span>
          )}
          <input
            ref={ref}
            className={`
              w-full px-4 py-2.5 rounded-xl text-sm
              backdrop-blur-sm
              transition-all duration-200
              focus:outline-none focus:ring-2
              ${icon ? 'pl-10' : ''}
              ${className}
            `}
            style={{
              background: 'var(--bg-card-inner)',
              border: error ? '1px solid rgba(220,38,38,0.5)' : '1px solid var(--glass-border-inner)',
              color: 'var(--color-text)',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent)';
              e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-ring)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = error ? 'rgba(220,38,38,0.5)' : 'var(--glass-border-inner)';
              e.currentTarget.style.boxShadow = '';
            }}
            {...props}
          />
        </div>
        {error && (
          <span className="text-xs text-error">{error}</span>
        )}
      </div>
    );
  }
);

GlassInput.displayName = 'GlassInput';
