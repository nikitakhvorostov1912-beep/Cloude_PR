import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GlassCard } from '@/components/glass/GlassCard';

describe('GlassCard', () => {
  it('renders children', () => {
    render(<GlassCard>Содержимое карточки</GlassCard>);
    expect(screen.getByText('Содержимое карточки')).toBeInTheDocument();
  });

  it('applies default glass class', () => {
    const { container } = render(<GlassCard>Test</GlassCard>);
    expect(container.firstChild).toHaveClass('glass');
  });

  it('applies subtle variant class', () => {
    const { container } = render(<GlassCard variant="subtle">Test</GlassCard>);
    expect(container.firstChild).toHaveClass('glass-subtle');
  });

  it('applies strong variant class', () => {
    const { container } = render(<GlassCard variant="strong">Test</GlassCard>);
    expect(container.firstChild).toHaveClass('glass-strong');
  });

  it('applies default padding (md = p-5)', () => {
    const { container } = render(<GlassCard>Test</GlassCard>);
    expect(container.firstChild).toHaveClass('p-5');
  });

  it('applies sm padding', () => {
    const { container } = render(<GlassCard padding="sm">Test</GlassCard>);
    expect(container.firstChild).toHaveClass('p-3');
  });

  it('applies lg padding', () => {
    const { container } = render(<GlassCard padding="lg">Test</GlassCard>);
    expect(container.firstChild).toHaveClass('p-7');
  });

  it('applies hoverable classes when hoverable=true', () => {
    const { container } = render(<GlassCard hoverable>Test</GlassCard>);
    expect(container.firstChild).toHaveClass('cursor-pointer');
  });

  it('applies custom className', () => {
    const { container } = render(<GlassCard className="my-custom">Test</GlassCard>);
    expect(container.firstChild).toHaveClass('my-custom');
  });

  it('renders complex children', () => {
    render(
      <GlassCard>
        <h2>Заголовок</h2>
        <p>Параграф текста</p>
      </GlassCard>
    );
    expect(screen.getByText('Заголовок')).toBeInTheDocument();
    expect(screen.getByText('Параграф текста')).toBeInTheDocument();
  });

  it('forwards ref', () => {
    const ref = { current: null };
    render(<GlassCard ref={ref}>Test</GlassCard>);
    expect(ref.current).not.toBeNull();
  });
});
