import { motion, type HTMLMotionProps } from 'motion/react';
import { forwardRef } from 'react';

interface GlassCardProps extends HTMLMotionProps<'div'> {
  variant?: 'default' | 'subtle' | 'strong';
  hoverable?: boolean;
  padding?: 'sm' | 'md' | 'lg';
}

const variantClasses = {
  default: 'glass',
  subtle: 'glass-subtle',
  strong: 'glass-strong',
};

const paddingClasses = {
  sm: 'p-3',
  md: 'p-5',
  lg: 'p-7',
};

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  ({ variant = 'default', hoverable = false, padding = 'md', className = '', children, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={`${variantClasses[variant]} ${paddingClasses[padding]} ${
          hoverable ? 'hover-lift cursor-pointer' : ''
        } ${className}`}
        whileHover={hoverable ? { y: -2 } : undefined}
        whileTap={hoverable ? { scale: 0.98 } : undefined}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

GlassCard.displayName = 'GlassCard';
