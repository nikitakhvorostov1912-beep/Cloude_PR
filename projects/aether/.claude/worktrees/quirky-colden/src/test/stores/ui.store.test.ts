import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useUIStore } from '@/stores/ui.store';

// Reset store before each test
function resetStore() {
  useUIStore.setState({
    sidebarCollapsed: false,
    activeRoute: '/',
    toasts: [],
    isLoading: false,
  });
}

describe('useUIStore', () => {
  beforeEach(() => {
    resetStore();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('initial state', () => {
    it('has correct defaults', () => {
      const state = useUIStore.getState();
      expect(state.sidebarCollapsed).toBe(false);
      expect(state.activeRoute).toBe('/');
      expect(state.toasts).toEqual([]);
      expect(state.isLoading).toBe(false);
    });
  });

  describe('toggleSidebar', () => {
    it('collapses sidebar', () => {
      useUIStore.getState().toggleSidebar();
      expect(useUIStore.getState().sidebarCollapsed).toBe(true);
    });

    it('toggles back to expanded', () => {
      useUIStore.getState().toggleSidebar();
      useUIStore.getState().toggleSidebar();
      expect(useUIStore.getState().sidebarCollapsed).toBe(false);
    });
  });

  describe('setActiveRoute', () => {
    it('updates active route', () => {
      useUIStore.getState().setActiveRoute('/dashboard');
      expect(useUIStore.getState().activeRoute).toBe('/dashboard');
    });

    it('handles empty string', () => {
      useUIStore.getState().setActiveRoute('');
      expect(useUIStore.getState().activeRoute).toBe('');
    });
  });

  describe('addToast', () => {
    it('adds a success toast', () => {
      useUIStore.getState().addToast('success', 'Готово', 'Операция завершена');
      const { toasts } = useUIStore.getState();
      expect(toasts).toHaveLength(1);
      expect(toasts[0].type).toBe('success');
      expect(toasts[0].title).toBe('Готово');
      expect(toasts[0].description).toBe('Операция завершена');
      expect(toasts[0].id).toMatch(/^toast-/);
    });

    it('adds multiple toasts', () => {
      useUIStore.getState().addToast('error', 'Ошибка 1');
      useUIStore.getState().addToast('info', 'Инфо');
      useUIStore.getState().addToast('warning', 'Внимание');
      expect(useUIStore.getState().toasts).toHaveLength(3);
    });

    it('auto-removes toast after 4 seconds', () => {
      useUIStore.getState().addToast('success', 'Тест');
      expect(useUIStore.getState().toasts).toHaveLength(1);
      vi.advanceTimersByTime(4000);
      expect(useUIStore.getState().toasts).toHaveLength(0);
    });

    it('does not remove before 4 seconds', () => {
      useUIStore.getState().addToast('success', 'Тест');
      vi.advanceTimersByTime(3999);
      expect(useUIStore.getState().toasts).toHaveLength(1);
    });

    it('adds toast without description', () => {
      useUIStore.getState().addToast('info', 'Только заголовок');
      expect(useUIStore.getState().toasts[0].description).toBeUndefined();
    });

    it('assigns unique ids to multiple toasts', () => {
      useUIStore.getState().addToast('success', 'Toast 1');
      useUIStore.getState().addToast('success', 'Toast 2');
      const { toasts } = useUIStore.getState();
      expect(toasts[0].id).not.toBe(toasts[1].id);
    });
  });

  describe('removeToast', () => {
    it('removes specific toast by id', () => {
      useUIStore.getState().addToast('success', 'Toast 1');
      useUIStore.getState().addToast('error', 'Toast 2');
      const id = useUIStore.getState().toasts[0].id;
      useUIStore.getState().removeToast(id);
      expect(useUIStore.getState().toasts).toHaveLength(1);
      expect(useUIStore.getState().toasts[0].title).toBe('Toast 2');
    });

    it('does nothing for non-existent id', () => {
      useUIStore.getState().addToast('success', 'Toast');
      useUIStore.getState().removeToast('non-existent');
      expect(useUIStore.getState().toasts).toHaveLength(1);
    });
  });

  describe('setLoading', () => {
    it('sets loading true', () => {
      useUIStore.getState().setLoading(true);
      expect(useUIStore.getState().isLoading).toBe(true);
    });

    it('sets loading false', () => {
      useUIStore.getState().setLoading(true);
      useUIStore.getState().setLoading(false);
      expect(useUIStore.getState().isLoading).toBe(false);
    });
  });
});
