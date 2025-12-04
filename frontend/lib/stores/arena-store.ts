/**
 * Arena Store - Battle state, active sessions
 */

import { create } from "zustand";
import type { BattleState, LiveSession, BacktestConfig, ForwardTestConfig, PlaybackSpeed, CandleData, AIThought, Trade } from "@/types";

interface ArenaState {
  // Active sessions
  liveSessions: LiveSession[];
  
  // Current battle (backtest) - session-specific data
  battleState: BattleState | null;
  backtestConfig: BacktestConfig | null;
  
  // Session data (candles, trades, thoughts) - keyed by sessionId
  sessionData: Record<string, {
    candles: CandleData[];
    trades: Trade[];
    thoughts: AIThought[];
    equity: number;
    pnl: number;
    status: string;
    currentCandle: number;
    totalCandles: number;
  }>;
  
  // Forward test config
  forwardConfig: ForwardTestConfig | null;
  
  // Battle controls
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;
  
  // Actions
  setBacktestConfig: (config: BacktestConfig) => void;
  setForwardConfig: (config: ForwardTestConfig) => void;
  startBattle: (sessionId: string) => void;
  pauseBattle: () => void;
  resumeBattle: () => void;
  stopBattle: () => void;
  setPlaybackSpeed: (speed: PlaybackSpeed) => void;
  
  // Session data actions
  addCandle: (sessionId: string, candle: CandleData) => void;
  addTrade: (sessionId: string, trade: Trade) => void;
  addThought: (sessionId: string, thought: AIThought) => void;
  updateSessionStats: (sessionId: string, stats: { equity?: number; pnl?: number; status?: string; currentCandle?: number; totalCandles?: number }) => void;
  clearSessionData: (sessionId: string) => void;
  seedSessionData: (
    sessionId: string,
    payload: Partial<{
      candles: CandleData[];
      trades: Trade[];
      thoughts: AIThought[];
      equity: number;
      pnl: number;
      status: string;
      currentCandle: number;
      totalCandles: number;
    }>
  ) => void;
  
  // Live sessions
  addLiveSession: (session: LiveSession) => void;
  removeLiveSession: (id: string) => void;
  updateLiveSession: (id: string, updates: Partial<LiveSession>) => void;
}

export const useArenaStore = create<ArenaState>((set, get) => ({
  // Active sessions
  liveSessions: [],
  
  // Battle state
  battleState: null,
  backtestConfig: null,
  forwardConfig: null,
  
  // Session data - keyed by sessionId
  sessionData: {},
  
  // Controls
  isPlaying: false,
  playbackSpeed: "normal",
  
  // Config setters
  setBacktestConfig: (config) => set({ backtestConfig: config }),
  setForwardConfig: (config) => set({ forwardConfig: config }),
  
  // Battle controls
  startBattle: (sessionId) =>
    set({
      battleState: {
        sessionId,
        status: "running",
        currentCandle: 0,
        totalCandles: 720, // 30 days of 1h candles
        elapsedTime: 0,
        currentPnL: 0,
        currentEquity: get().backtestConfig?.capital || 10000,
        openPosition: null,
        trades: [],
        aiThoughts: [],
      },
      isPlaying: true,
      // Initialize session data
      sessionData: {
        ...get().sessionData,
        [sessionId]: {
          candles: [],
          trades: [],
          thoughts: [],
          equity: get().backtestConfig?.capital || 10000,
          pnl: 0,
          status: "running",
          currentCandle: 0,
          totalCandles: 0,
        },
      },
    }),
  pauseBattle: () =>
    set((state) => ({
      isPlaying: false,
      battleState: state.battleState
        ? { ...state.battleState, status: "paused" }
        : null,
    })),
  resumeBattle: () =>
    set((state) => ({
      isPlaying: true,
      battleState: state.battleState
        ? { ...state.battleState, status: "running" }
        : null,
    })),
  stopBattle: () =>
    set((state) => ({
      isPlaying: false,
      battleState: state.battleState
        ? { ...state.battleState, status: "completed" }
        : null,
    })),
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),
  
  // Session data actions
  addCandle: (sessionId, candle) =>
    set((state) => {
      const session = state.sessionData[sessionId] || {
        candles: [],
        trades: [],
        thoughts: [],
        equity: 0,
        pnl: 0,
        status: "running",
        currentCandle: 0,
        totalCandles: 0,
      };
      return {
        sessionData: {
          ...state.sessionData,
          [sessionId]: {
            ...session,
            candles: [...session.candles, candle],
          },
        },
      };
    }),
  addTrade: (sessionId, trade) =>
    set((state) => {
      const session = state.sessionData[sessionId] || {
        candles: [],
        trades: [],
        thoughts: [],
        equity: 0,
        pnl: 0,
        status: "running",
        currentCandle: 0,
        totalCandles: 0,
      };
      return {
        sessionData: {
          ...state.sessionData,
          [sessionId]: {
            ...session,
            trades: [trade, ...session.trades].slice(0, 100), // Keep last 100 trades
          },
        },
      };
    }),
  addThought: (sessionId, thought) =>
    set((state) => {
      const session = state.sessionData[sessionId] || {
        candles: [],
        trades: [],
        thoughts: [],
        equity: 0,
        pnl: 0,
        status: "running",
        currentCandle: 0,
        totalCandles: 0,
      };
      return {
        sessionData: {
          ...state.sessionData,
          [sessionId]: {
            ...session,
            thoughts: [thought, ...session.thoughts].slice(0, 50), // Keep last 50 thoughts
          },
        },
      };
    }),
  updateSessionStats: (sessionId, stats) =>
    set((state) => {
      const session = state.sessionData[sessionId] || {
        candles: [],
        trades: [],
        thoughts: [],
        equity: 0,
        pnl: 0,
        status: "running",
        currentCandle: 0,
        totalCandles: 0,
      };
      return {
        sessionData: {
          ...state.sessionData,
          [sessionId]: {
            ...session,
            ...stats,
          },
        },
      };
    }),
  clearSessionData: (sessionId) =>
    set((state) => {
      const { [sessionId]: _, ...rest } = state.sessionData;
      return { sessionData: rest };
    }),
  seedSessionData: (sessionId, payload) =>
    set((state) => {
      const session = state.sessionData[sessionId] || {
        candles: [],
        trades: [],
        thoughts: [],
        equity: 0,
        pnl: 0,
        status: "running",
        currentCandle: 0,
        totalCandles: 0,
      };
      return {
        sessionData: {
          ...state.sessionData,
          [sessionId]: {
            ...session,
            ...payload,
          },
        },
      };
    }),
  
  // Live sessions
  addLiveSession: (session) =>
    set((state) => ({ liveSessions: [...state.liveSessions, session] })),
  removeLiveSession: (id) =>
    set((state) => ({
      liveSessions: state.liveSessions.filter((s) => s.id !== id),
    })),
  updateLiveSession: (id, updates) =>
    set((state) => ({
      liveSessions: state.liveSessions.map((s) =>
        s.id === id ? { ...s, ...updates } : s
      ),
    })),
}));

