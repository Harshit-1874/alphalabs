/**
 * Arena Store - Battle state, active sessions
 */

import { create } from "zustand";
import type { BattleState, LiveSession, BacktestConfig, ForwardTestConfig, PlaybackSpeed, CandleData, AIThought, Trade } from "@/types";

type SessionSnapshot = {
  candles: CandleData[];
  trades: Trade[];
  thoughts: AIThought[];
  equity: number;
  pnl: number;
  status: string;
  currentCandle: number;
  totalCandles: number;
  startedAt?: Date;
  asset?: string;
  agentId?: string;
  winRate?: number;
};

interface ArenaState {
  // Active sessions
  liveSessions: LiveSession[];
  
  // Current battle (backtest) - session-specific data
  battleState: BattleState | null;
  backtestConfig: BacktestConfig | null;
  activeSessionId: string | null;
  
  // Session data (candles, trades, thoughts) - keyed by sessionId
  sessionData: Record<string, SessionSnapshot>;
  
  // Forward test config
  forwardConfig: ForwardTestConfig | null;
  
  // Battle controls
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;
  
  // Actions
  setBacktestConfig: (config: BacktestConfig) => void;
  setForwardConfig: (config: ForwardTestConfig) => void;
  setActiveSessionId: (sessionId: string) => void;
  clearActiveSessionId: () => void;
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
  upsertLiveBacktest: (session: {
    id: string;
    asset: string;
    status: string;
    startedAt: Date;
    pnl: number;
    progress: number;
  }) => void;
}

export const useArenaStore = create<ArenaState>((set, get) => ({
  // Active sessions
  liveSessions: [],
  
  // Battle state
  battleState: null,
  backtestConfig: null,
  activeSessionId: null,
  forwardConfig: null,
  
  // Session data - keyed by sessionId
  sessionData: {},
  
  // Controls
  isPlaying: false,
  playbackSpeed: "normal",
  
  // Config setters
  setBacktestConfig: (config) => set({ backtestConfig: config }),
  setForwardConfig: (config) => set({ forwardConfig: config }),
  setActiveSessionId: (sessionId) => set({ activeSessionId: sessionId }),
  clearActiveSessionId: () => set({ activeSessionId: null }),
  
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
      let nextCandles = [...session.candles, candle];

      // Deduplicate by candle time, keeping the latest entry for a given timestamp
      const map = new Map<number, typeof candle>();
      nextCandles.forEach((item) => {
        map.set(item.time, item);
      });
      nextCandles = Array.from(map.values()).sort((a, b) => a.time - b.time);

      return {
        sessionData: {
          ...state.sessionData,
          [sessionId]: {
            ...session,
            candles: nextCandles,
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
      
      // Deduplicate by trade_number if available, otherwise by id
      const existingIndex = trade.tradeNumber !== undefined
        ? session.trades.findIndex(t => t.tradeNumber === trade.tradeNumber)
        : session.trades.findIndex(t => t.id === trade.id);
      
      let updatedTrades = [...session.trades];
      if (existingIndex >= 0) {
        // Update existing trade
        updatedTrades[existingIndex] = trade;
      } else {
        // Add new trade at the beginning
        updatedTrades = [trade, ...updatedTrades];
      }
      
      // Sort by trade_number descending (newest first), then limit to 100
      updatedTrades.sort((a, b) => {
        if (a.tradeNumber !== undefined && b.tradeNumber !== undefined) {
          return b.tradeNumber - a.tradeNumber;
        }
        return b.exitTime.getTime() - a.exitTime.getTime();
      });
      
      return {
        sessionData: {
          ...state.sessionData,
          [sessionId]: {
            ...session,
            trades: updatedTrades.slice(0, 100), // Keep last 100 trades
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
  upsertLiveBacktest: (session) =>
    set((state) => {
      const existing = state.liveSessions.find((s) => s.id === session.id);
      if (existing) {
        return {
          liveSessions: state.liveSessions.map((s) =>
            s.id === session.id
              ? {
                  ...s,
                  asset: session.asset,
                  pnl: session.pnl,
                  progress: session.progress,
                  status: session.status as "running" | "paused",
                }
              : s
          ),
        };
      }
      return {
        liveSessions: [
          ...state.liveSessions,
          {
            id: session.id,
            agentId: state.backtestConfig?.agentId || "",
            agentName:
              state.backtestConfig?.agentId ||
              state.battleState?.sessionId ||
              "Agent",
            asset: session.asset,
            startedAt: session.startedAt,
            duration: "–",
            pnl: session.pnl,
            trades: 0,
            winRate: 0,
            status: session.status as "running" | "paused",
          },
        ],
      };
    }),
}));

