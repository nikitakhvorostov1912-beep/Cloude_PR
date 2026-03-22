import { motion } from 'motion/react';
import type { ReactNode, MouseEvent } from 'react';

interface GlassButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  icon?: ReactNode;
  loading?: boolean;
  disabled?: boolean;
  children?: ReactNode;
  className?: string;
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void;
  type?: 'button' | 'submit' | 'reset';
  title?: string;
}

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm gap-1.5 rounded-lg',
  md: 'px-5 py-2.5 text-sm gap-2 rounded-xl',
  lg: 'px-7 py-3.5 text-base gap-2.5 rounded-xl',
};

const variantInlineStyles: Record<string, React.CSSProperties> = {
  primary: {
    background: 'var(--accent)',
    color: 'white',
    border: '1px solid rgba(91,79,212,0.3)',
    boxShadow: '0 4px 16px rgba(91,79,212,0.3)',
  },
  secondary: {
    background: 'var(--bg-card-inner)',
    color: 'var(--color-text)',
    border: '1px solid var(--glass-border-inner)',
    boxShadow: 'var(--shadow-card)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--color-text-secondary)',
    border: '1px solid transparent',
  },
  danger: {
    background: 'rgba(220,38,38,0.9)',
    color: 'white',
    border: '1px solid rgba(220,38,38,0.3)',
    boxShadow: '0 4px 16px rgba(220,38,38,0.3)',
  },
};

export function GlassButton({
  variant = 'primary',
  size = 'md',
  icon,
  loading = false,
  children,
  disabled,
  className = '',
  onClick,
  type = 'button',
  title,
}: GlassButtonProps) {
  return (
    <motion.button
      type={type}
      title={title}
      className={`
        inline-flex items-center justify-center font-medium
        backdrop-blur-sm transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${sizeStyles[size]}
        ${className}
      `}
      style={variantInlineStyles[variant]}
      onMouseEnter={(e) => {
        if (disabled) return;
        if (variant === 'primary') {
          e.currentTarget.style.background = 'var(--accent-light)';
          e.currentTarget.style.boxShadow = '0 6px 24px rgba(91,79,212,0.4)';
        } else if (variant === 'ghost') {
          e.currentTarget.style.background = 'var(--accent-dim)';
          e.currentTarget.style.color = 'var(--color-text)';
        } else if (variant === 'secondary') {
          e.currentTarget.style.background = 'rgba(255,255,255,0.55)';
        }
      }}
      onMouseLeave={(e) => {
        if (disabled) return;
        const base = variantInlineStyles[variant];
        e.currentTarget.style.background = base.background as string;
        e.currentTarget.style.boxShadow = (base.boxShadow as string) ?? '';
        if (variant === 'ghost') {
          e.currentTarget.style.color = 'var(--color-text-secondary)';
        }
      }}
      whileHover={!disabled ? { scale: 1.02, y: -1 } : undefined}
      whileTap={!disabled ? { scale: 0.97, y: 0 } : undefined}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading ? (
        <motion.div
          className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
        />
      ) : icon ? (
        <span className="flex-shrink-0">{icon}</span>
      ) : null}
      {children}
    </motion.button>
  );
}
