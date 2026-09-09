import { create } from "zustand";

interface UiState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  toggleSidebarCollapsed: () => void;
  closeSidebar: () => void;
  themeMode: "dark" | "light";
  toggleThemeMode: () => void;
}

/**
 * Global UI-only state (never server data -- that's React Query's job).
 * Theme mode is dark-first per spec; light mode is a real, working toggle
 * but the design system is optimized for dark (SOC dashboards run dark).
 */
export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: false,
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleSidebarCollapsed: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  closeSidebar: () => set({ sidebarOpen: false }),
  themeMode: "dark",
  toggleThemeMode: () => set((s) => ({ themeMode: s.themeMode === "dark" ? "light" : "dark" })),
}));
