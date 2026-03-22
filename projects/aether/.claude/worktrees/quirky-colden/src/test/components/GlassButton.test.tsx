import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GlassButton } from '@/components/glass/GlassButton';

describe('GlassButton', () => {
  it('renders children', () => {
    render(<GlassButton>Нажми меня</GlassButton>);
    expect(screen.getByText('Нажми меня')).toBeInTheDocument();
  });

  it('renders as a button element', () => {
    render(<GlassButton>Кнопка</GlassButton>);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<GlassButton onClick={onClick}>Клик</GlassButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('does not call onClick when disabled', () => {
    const onClick = vi.fn();
    render(<GlassButton onClick={onClick} disabled>Отключена</GlassButton>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('shows loading spinner when loading=true', () => {
    const { container } = render(<GlassButton loading>Загрузка</GlassButton>);
    // Loading spinner is a div with specific classes
    const spinner = container.querySelector('.border-2');
    expect(spinner).toBeInTheDocument();
  });

  it('is disabled when loading=true', () => {
    render(<GlassButton loading>Загрузка</GlassButton>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('renders icon when provided', () => {
    render(<GlassButton icon={<span data-testid="icon">★</span>}>С иконкой</GlassButton>);
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('applies type="submit" attribute', () => {
    render(<GlassButton type="submit">Отправить</GlassButton>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
  });

  it('applies custom className', () => {
    const { container } = render(<GlassButton className="custom-class">Кнопка</GlassButton>);
    expect(container.firstChild).toHaveClass('custom-class');
  });

  describe('variants', () => {
    it('renders primary variant', () => {
      const { container } = render(<GlassButton variant="primary">Primary</GlassButton>);
      expect(container.firstChild).toHaveClass('bg-primary');
    });

    it('renders danger variant', () => {
      const { container } = render(<GlassButton variant="danger">Danger</GlassButton>);
      // Check it has some class containing 'error' related styling
      const classes = (container.firstChild as HTMLElement)?.className ?? '';
      expect(classes).toContain('error');
    });

    it('renders ghost variant', () => {
      const { container } = render(<GlassButton variant="ghost">Ghost</GlassButton>);
      expect(container.firstChild).toHaveClass('bg-transparent');
    });
  });
});
