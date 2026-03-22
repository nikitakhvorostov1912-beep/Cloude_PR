import { motion } from 'motion/react';
import type { ReactNode } from 'react';

interface GlassButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  icon?: ReactNode;
  loading?: boolean;
  disabled?: boolean;
  children?: ReactNode;
  className?: string;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
}

const variantStyles = {
  primary:
    'bg-primary text-white border-primary/30 shadow-[0_4px_16px_rgba(108,92,231,0.3)] hover:shadow-[0_6px_24px_rgba(108,92,231,0.4)] hover:bg-primary-dark',
  secondary:
    'bg-white/60 text-text border-white/30 shadow-[0_4px_16px_rgba(108,92,231,0.08)] hover:bg-white/75',
  ghost:
    'bg-transparent text-text-secondary border-transparent hover:bg-white/40 hover:text-text',
  danger:
    'bg-error/90 text-white border-error/30 shadow-[0_4px_16px_rgba(225,112,85,0.3)] hover:bg-error',
};

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm gap-1.5 rounded-lg',
  md: 'px-5 py-2.5 text-sm gap-2 rounded-xl',
  lg: 'px-7 py-3.5 text-base gap-2.5 rounded-xl',
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
}: GlassButtonProps) {
  return (
    <motion.button
      type={type}
      className={`
        inline-flex items-center justify-center font-medium
        backdrop-blur-sm border transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${className}
      `}
      whileHover={!disabled ? { scale: 1.02 } : undefined}
      whileTap={!disabled ? { scale: 0.97 } : undefined}
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
