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
          <label className="text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            className={`
              w-full px-4 py-2.5 rounded-xl text-sm
              bg-white/50 backdrop-blur-sm
              border border-white/30
              text-text placeholder:text-text-muted
              focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50
              transition-all duration-200
              ${icon ? 'pl-10' : ''}
              ${error ? 'border-error/50 focus:ring-error/30' : ''}
              ${className}
            `}
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
