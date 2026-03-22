import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GlassToastContainer } from '@/components/glass/GlassToast';
import { useUIStore } from '@/stores/ui.store';

describe('GlassToastContainer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useUIStore.setState({
      sidebarCollapsed: false,
      activeRoute: '/',
      toasts: [],
      isLoading: false,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders empty container initially', () => {
    const { container } = render(<GlassToastContainer />);
    // The container div exists but has no toast children
    const toastItems = container.querySelectorAll('.glass-strong');
    expect(toastItems).toHaveLength(0);
  });

  it('renders success toast', () => {
    useUIStore.setState({
      toasts: [{ id: 'toast-1', type: 'success', title: 'Успешно' }],
    } as Partial<Parameters<typeof useUIStore.setState>[0]>);
    render(<GlassToastContainer />);
    expect(screen.getByText('Успешно')).toBeInTheDocument();
  });

  it('renders error toast', () => {
    useUIStore.setState({
      toasts: [{ id: 'toast-1', type: 'error', title: 'Ошибка', description: 'Что-то пошло не так' }],
    } as Partial<Parameters<typeof useUIStore.setState>[0]>);
    render(<GlassToastContainer />);
    expect(screen.getByText('Ошибка')).toBeInTheDocument();
    expect(screen.getByText('Что-то пошло не так')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    useUIStore.setState({
      toasts: [{ id: 't1', type: 'info', title: 'Инфо', description: 'Дополнительная информация' }],
    } as Partial<Parameters<typeof useUIStore.setState>[0]>);
    render(<GlassToastContainer />);
    expect(screen.getByText('Дополнительная информация')).toBeInTheDocument();
  });

  it('removes toast on click', () => {
    useUIStore.setState({
      toasts: [{ id: 'toast-click', type: 'success', title: 'Кликни чтобы закрыть' }],
    } as Partial<Parameters<typeof useUIStore.setState>[0]>);
    render(<GlassToastContainer />);
    const toast = screen.getByText('Кликни чтобы закрыть').closest('[class*="glass-strong"]');
    expect(toast).not.toBeNull();
    fireEvent.click(toast!);
    expect(useUIStore.getState().toasts).toHaveLength(0);
  });

  it('renders multiple toasts', () => {
    useUIStore.setState({
      toasts: [
        { id: 't1', type: 'success', title: 'Toast 1' },
        { id: 't2', type: 'error', title: 'Toast 2' },
        { id: 't3', type: 'warning', title: 'Toast 3' },
      ],
    } as Partial<Parameters<typeof useUIStore.setState>[0]>);
    render(<GlassToastContainer />);
    expect(screen.getByText('Toast 1')).toBeInTheDocument();
    expect(screen.getByText('Toast 2')).toBeInTheDocument();
    expect(screen.getByText('Toast 3')).toBeInTheDocument();
  });
});
