/**
 * Sessions Store - Active forward and backtest sessions
 * Centralized state management for active sessions to avoid duplicate API calls
 */

import { create } from "zustand";
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

// Reactive selectors - these create subscriptions when used in components
export const selectAllSessions = (state: SessionsState): ForwardSession[] => 
  [...state.forwardSessions, ...state.backtestSessions];

export const selectActiveSessions = (state: SessionsState): ForwardSession[] => 
  [...state.forwardSessions, ...state.backtestSessions]
    .filter(s => s.status === "running" || s.status === "paused");


