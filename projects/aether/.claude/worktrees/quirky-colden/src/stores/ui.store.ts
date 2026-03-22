import { create } from 'zustand';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
}

interface UIState {
  sidebarCollapsed: boolean;
  activeRoute: string;
  toasts: Toast[];
  isLoading: boolean;
  toggleSidebar: () => void;
  setActiveRoute: (route: string) => void;
  addToast: (type: ToastType, title: string, description?: string) => void;
  removeToast: (id: string) => void;
  setLoading: (loading: boolean) => void;
}

let toastCounter = 0;

export const useUIStore = create<UIState>()((set) => ({
  sidebarCollapsed: false,
  activeRoute: '/',
  toasts: [],
  isLoading: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setActiveRoute: (route) => set({ activeRoute: route }),
  addToast: (type, title, description) => {
    const id = `toast-${++toastCounter}`;
    set((s) => ({ toasts: [...s.toasts, { id, type, title, description }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, 4000);
  },
  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  setLoading: (loading) => set({ isLoading: loading }),
}));
