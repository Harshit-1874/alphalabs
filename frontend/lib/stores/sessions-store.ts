/**
 * Sessions Store - Active forward and backtest sessions
 * Centralized state management for active sessions to avoid duplicate API calls
 */

import { create } from "zustand";
import { useMemo } from "react";
import type { ForwardSession } from "@/hooks/use-forward-sessions";

interface SessionsState {
  // Data
  forwardSessions: ForwardSession[];
  backtestSessions: ForwardSession[];
  
  // Loading and error states
  isLoading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
  
  // Actions
  setForwardSessions: (sessions: ForwardSession[]) => void;
  setBacktestSessions: (sessions: ForwardSession[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setLastFetchedAt: (timestamp: number) => void;
  
  // Refresh trigger
  refreshKey: number;
  triggerRefresh: () => void;
}

export const useSessionsStore = create<SessionsState>((set) => ({
  // Initial state
  forwardSessions: [],
  backtestSessions: [],
  isLoading: false,
  error: null,
  lastFetchedAt: null,
  refreshKey: 0,
  
  // Actions
  setForwardSessions: (sessions) => set({ forwardSessions: sessions }),
  setBacktestSessions: (sessions) => set({ backtestSessions: sessions }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setLastFetchedAt: (timestamp) => set({ lastFetchedAt: timestamp }),
  triggerRefresh: () => set((state) => ({ refreshKey: state.refreshKey + 1 })),
}));

// Selectors that create new array references - use with shallow comparison
// NOTE: These selectors create new arrays on every call, which means they will
// trigger re-renders on ANY store change (not just session changes) unless
// used with shallow comparison. Use the helper hooks below for optimal performance.
export const selectAllSessions = (state: SessionsState): ForwardSession[] => 
  [...state.forwardSessions, ...state.backtestSessions];

export const selectActiveSessions = (state: SessionsState): ForwardSession[] => 
  [...state.forwardSessions, ...state.backtestSessions]
    .filter(s => s.status === "running" || s.status === "paused");

// Helper hooks that prevent unnecessary re-renders by memoizing based on actual session data
// These only trigger re-renders when the actual session arrays change, not on other store updates
export const useAllSessions = (): ForwardSession[] => {
  const forwardSessions = useSessionsStore((state) => state.forwardSessions);
  const backtestSessions = useSessionsStore((state) => state.backtestSessions);
  
  return useMemo(
    () => [...forwardSessions, ...backtestSessions],
    [forwardSessions, backtestSessions]
  );
};

export const useActiveSessions = (): ForwardSession[] => {
  const forwardSessions = useSessionsStore((state) => state.forwardSessions);
  const backtestSessions = useSessionsStore((state) => state.backtestSessions);
  
  return useMemo(
    () => 
      [...forwardSessions, ...backtestSessions]
        .filter(s => s.status === "running" || s.status === "paused"),
    [forwardSessions, backtestSessions]
  );
};


