import { create } from "zustand";

// ----------------------------------------------------------------
// Global application state
// ----------------------------------------------------------------

interface AppState {
  /** ID of the currently selected project (null when none selected) */
  currentProjectId: string | null;
  setCurrentProject: (id: string | null) => void;

  /** Sidebar visibility */
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentProjectId: null,
  setCurrentProject: (id) => set({ currentProjectId: id }),

  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
