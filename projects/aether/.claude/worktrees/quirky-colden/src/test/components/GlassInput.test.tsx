import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GlassInput } from '@/components/glass/GlassInput';

describe('GlassInput', () => {
  it('renders an input element', () => {
    render(<GlassInput />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders label when provided', () => {
    render(<GlassInput label="API Ключ" />);
    expect(screen.getByText('API Ключ')).toBeInTheDocument();
  });

  it('does not render label when not provided', () => {
    const { container } = render(<GlassInput />);
    expect(container.querySelector('label')).not.toBeInTheDocument();
  });

  it('renders error message', () => {
    render(<GlassInput error="Обязательное поле" />);
    expect(screen.getByText('Обязательное поле')).toBeInTheDocument();
  });

  it('does not render error when not provided', () => {
    const { container } = render(<GlassInput />);
    expect(container.querySelector('.text-error')).not.toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(<GlassInput icon={<span data-testid="lock-icon">🔒</span>} />);
    expect(screen.getByTestId('lock-icon')).toBeInTheDocument();
  });

  it('accepts user input', () => {
    const onChange = vi.fn();
    render(<GlassInput onChange={onChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'sk-test-key' } });
    expect(onChange).toHaveBeenCalled();
  });

  it('applies placeholder text', () => {
    render(<GlassInput placeholder="Введите ключ" />);
    expect(screen.getByPlaceholderText('Введите ключ')).toBeInTheDocument();
  });

  it('renders as password type', () => {
    render(<GlassInput type="password" />);
    const input = document.querySelector('input[type="password"]');
    expect(input).toBeInTheDocument();
  });

  it('applies disabled state', () => {
    render(<GlassInput disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('applies custom className to input', () => {
    render(<GlassInput className="custom-input" />);
    expect(screen.getByRole('textbox')).toHaveClass('custom-input');
  });

  it('forwards ref to input element', () => {
    const ref = { current: null };
    render(<GlassInput ref={ref} />);
    expect(ref.current).not.toBeNull();
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });

  it('applies error styling to input when error is provided', () => {
    render(<GlassInput error="Ошибка" />);
    const input = screen.getByRole('textbox');
    expect(input.className).toContain('error');
  });
});
