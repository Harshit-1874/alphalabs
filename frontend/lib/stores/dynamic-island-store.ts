/**
 * Dynamic Island Store
 * Manages the global Dynamic Island state for AI presence, notifications, and celebrations
 */

import { create } from "zustand";
import type { SizePresets } from "@/components/ui/dynamic-island";

// Island display modes
export type IslandMode =
  | "hidden"
  | "idle"
  | "analyzing"
  | "narrator"
  | "trade"
  | "alpha"
  | "celebration"
  | "connection"
  | "liveSession";

// Data types for different modes - enhanced with expanded view data
export interface TradeData {
  direction: "long" | "short";
  asset: string;
  entryPrice: number;
  confidence?: number;
  // Expanded view data
  stopLoss?: number;
  takeProfit?: number;
  positionSize?: number;
  leverage?: number;
  reasoning?: string;
  timestamp?: number;
}

export interface NarratorData {
  text: string;
  type?: "info" | "action" | "result";
  // Expanded view data
  details?: string;
  metrics?: { label: string; value: string }[];
}

export interface CelebrationData {
  pnl: number;
  trades?: number;
  winRate?: number;
  // Expanded view data
  bestTrade?: { asset: string; pnl: number };
  worstTrade?: { asset: string; pnl: number };
  totalVolume?: number;
  duration?: string;
  sharpeRatio?: number;
}

export interface AlphaData {
  asset: string;
  direction: "long" | "short";
  confidence: number;
  reason?: string;
  // Expanded view data
  indicators?: { name: string; signal: "bullish" | "bearish" | "neutral"; value?: string }[];
  targetPrice?: number;
  riskReward?: number;
  timeframe?: string;
}

export interface ConnectionData {
  status: "connected" | "disconnected" | "reconnecting";
  // Expanded view data
  latency?: number;
  lastUpdate?: number;
  exchange?: string;
}

export interface LiveSessionData {
  agentName: string;
  pnl: number;
  duration: string;
  status: "running" | "paused";
  // Expanded view data
  openPositions?: number;
  totalTrades?: number;
  winRate?: number;
  equity?: number;
  nextDecisionIn?: string;
}

export interface AnalyzingData {
  message?: string;
  // Expanded view data
  phase?: "scanning" | "analyzing" | "deciding" | "executing";
  progress?: number;
  currentAsset?: string;
  candlesProcessed?: number;
  totalCandles?: number;
}

export type IslandData =
  | TradeData
  | NarratorData
  | CelebrationData
  | AlphaData
  | ConnectionData
  | LiveSessionData
  | AnalyzingData
  | null;

interface DynamicIslandState {
  // Current state
  mode: IslandMode;
  size: SizePresets;
  data: IslandData;
  isVisible: boolean;
  isExpanded: boolean; // Track if user has expanded the island (hover/click)

  // Queue for narrator messages
  narratorQueue: NarratorData[];
  isProcessingQueue: boolean;

  // Auto-dismiss timer
  dismissTimeout: number | null;

  // Actions
  show: () => void;
  hide: () => void;
  setExpanded: (expanded: boolean) => void;

  // Mode-specific actions
  showIdle: () => void;
  showAnalyzing: (data?: AnalyzingData) => void;
  narrate: (text: string, type?: NarratorData["type"], details?: NarratorData) => void;
  showTradeExecuted: (trade: TradeData) => void;
  showAlphaDetected: (alpha: AlphaData) => void;
  celebrate: (data: CelebrationData) => void;
  showConnectionStatus: (data: ConnectionData) => void;
  showLiveSession: (session: LiveSessionData) => void;

  // Internal
  _processNarratorQueue: () => void;
  _scheduleAutoDismiss: (delay: number) => void;
  _clearDismissTimeout: () => void;
}

// Helper to get size preset based on mode
const getSizeForMode = (mode: IslandMode): SizePresets => {
  switch (mode) {
    case "hidden":
      return "default";
    case "idle":
      return "default";
    case "analyzing":
      return "compact";
    case "narrator":
      return "large";
    case "trade":
      return "large";
    case "alpha":
      return "tall";
    case "celebration":
      return "tall";
    case "connection":
      return "compact";
    case "liveSession":
      return "compact";
    default:
      return "default";
  }
};

export const useDynamicIslandStore = create<DynamicIslandState>((set, get) => ({
  // Initial state
  mode: "hidden",
  size: "default",
  data: null,
  isVisible: false,
  isExpanded: false,
  narratorQueue: [],
  isProcessingQueue: false,
  dismissTimeout: null,

  // Basic visibility
  show: () => set({ isVisible: true }),
  hide: () => {
    get()._clearDismissTimeout();
    set({ isVisible: false, mode: "hidden", data: null, isExpanded: false });
  },
  setExpanded: (expanded: boolean) => set({ isExpanded: expanded }),

  // Show idle state (AI is ready but not doing anything)
  showIdle: () => {
    get()._clearDismissTimeout();
    set({
      mode: "idle",
      size: getSizeForMode("idle"),
      data: null,
      isVisible: true,
    });
  },

  // Show analyzing state (AI is processing)
  showAnalyzing: (data?: AnalyzingData) => {
    get()._clearDismissTimeout();
    set({
      mode: "analyzing",
      size: getSizeForMode("analyzing"),
      data: data || { message: "Analyzing..." },
      isVisible: true,
    });
  },

  // Narrate text (queued) - now accepts full NarratorData for expanded info
  narrate: (text: string, type: NarratorData["type"] = "info", extraData?: NarratorData) => {
    const state = get();
    const newData: NarratorData = { text, type, ...extraData };

    // If currently showing narrator, queue the message
    if (state.mode === "narrator" && state.isProcessingQueue) {
      set({ narratorQueue: [...state.narratorQueue, newData] });
    } else {
      // Show immediately and start processing
      set({
        mode: "narrator",
        size: getSizeForMode("narrator"),
        data: newData,
        isVisible: true,
        isProcessingQueue: true,
      });
      get()._scheduleAutoDismiss(8000); // Increased from 5000 to 8000ms - let AI thoughts breathe
    }
  },

  // Show trade executed
  showTradeExecuted: (trade: TradeData) => {
    get()._clearDismissTimeout();
    set({
      mode: "trade",
      size: getSizeForMode("trade"),
      data: { ...trade, timestamp: trade.timestamp || Date.now() },
      isVisible: true,
    });
    get()._scheduleAutoDismiss(12000); // Increased from 7000 to 12000ms - let trade info breathe
  },

  // Show alpha detected
  showAlphaDetected: (alpha: AlphaData) => {
    get()._clearDismissTimeout();
    set({
      mode: "alpha",
      size: getSizeForMode("alpha"),
      data: alpha,
      isVisible: true,
    });
    get()._scheduleAutoDismiss(8000); // Important - let it stay
  },

  // Celebrate profit
  celebrate: (data: CelebrationData) => {
    get()._clearDismissTimeout();
    set({
      mode: "celebration",
      size: getSizeForMode("celebration"),
      data: data,
      isVisible: true,
    });
    get()._scheduleAutoDismiss(10000); // Celebration - let it shine!
  },

  // Show connection status - now accepts full ConnectionData
  showConnectionStatus: (data: ConnectionData) => {
    get()._clearDismissTimeout();
    set({
      mode: "connection",
      size: getSizeForMode("connection"),
      data: data,
      isVisible: true,
    });

    // Auto-dismiss after 4s for connected, stay visible for disconnected
    if (data.status === "connected") {
      get()._scheduleAutoDismiss(4000);
    }
  },

  // Show live session status
  showLiveSession: (session: LiveSessionData) => {
    get()._clearDismissTimeout();
    set({
      mode: "liveSession",
      size: getSizeForMode("liveSession"),
      data: session,
      isVisible: true,
    });
    // Don't auto-dismiss - stay visible while session is running
  },

  // Process narrator queue
  _processNarratorQueue: () => {
    const state = get();
    if (state.narratorQueue.length > 0) {
      const [next, ...rest] = state.narratorQueue;
      set({
        data: next,
        narratorQueue: rest,
      });
      get()._scheduleAutoDismiss(8000); // Increased from 5000 to 8000ms - let each AI thought breathe
    } else {
      // Queue empty, return to idle
      set({ isProcessingQueue: false });
      get()._scheduleAutoDismiss(3000); // Wait a bit before going idle
    }
  },

  // Schedule auto-dismiss
  _scheduleAutoDismiss: (delay: number) => {
    get()._clearDismissTimeout();
    const timeout = window.setTimeout(() => {
      const state = get();

      // If narrator mode, process queue first
      if (state.mode === "narrator" && state.narratorQueue.length > 0) {
        state._processNarratorQueue();
      } else {
        // Return to idle or hide
        set({
          mode: "idle",
          size: getSizeForMode("idle"),
          data: null,
          isProcessingQueue: false,
        });
      }
    }, delay);
    set({ dismissTimeout: timeout as unknown as number });
  },

  // Clear dismiss timeout
  _clearDismissTimeout: () => {
    const timeout = get().dismissTimeout;
    if (timeout) {
      window.clearTimeout(timeout);
      set({ dismissTimeout: null });
    }
  },
}));

