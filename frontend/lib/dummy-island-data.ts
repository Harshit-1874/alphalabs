/**
 * Dummy Data for Dynamic Island
 * Replace these with actual API calls / WebSocket events in production
 */

import type {
  TradeData,
  NarratorData,
  CelebrationData,
  AlphaData,
  ConnectionData,
} from "@/lib/stores/dynamic-island-store";

// ============================================
// NARRATOR MESSAGES
// Replace with actual AI analysis messages from backend
// ============================================

export const NARRATOR_MESSAGES = {
  // Backtest lifecycle
  backtestStart: "Initializing backtest simulation...",
  backtestAnalyzing: "Scanning historical price data...",
  backtestComplete: "Backtest simulation complete",
  
  // Forward test lifecycle
  forwardStart: "Connecting to live market feed...",
  forwardAnalyzing: "Monitoring real-time market conditions...",
  forwardPaused: "Session paused - positions held",
  forwardResumed: "Resuming live analysis...",
  
  // AI analysis phases
  analyzing: "Analyzing market structure...",
  identifyingPatterns: "Identifying price patterns...",
  evaluatingSetup: "Evaluating trade setup...",
  calculatingRisk: "Calculating risk parameters...",
  waitingForEntry: "Waiting for optimal entry...",
  
  // Trade actions
  enteringLong: "Entering long position...",
  enteringShort: "Entering short position...",
  takingProfit: "Take profit triggered!",
  stoppingLoss: "Stop loss activated",
  closingPosition: "Closing position...",
  
  // Market observations
  bullishMomentum: "Detecting bullish momentum...",
  bearishPressure: "Bearish pressure building...",
  consolidation: "Market consolidating...",
  breakoutDetected: "Breakout detected!",
  reversalSignal: "Potential reversal forming...",
} as const;

// ============================================
// MOCK TRADE DATA
// Replace with actual trade execution data from backend
// ============================================

export const createMockTradeData = (
  direction: "long" | "short",
  asset: string = "BTC/USDT",
  entryPrice?: number
): TradeData => ({
  direction,
  asset,
  entryPrice: entryPrice ?? (direction === "long" ? 43250 : 43180),
  confidence: Math.floor(Math.random() * 20) + 75, // 75-95%
});

// ============================================
// MOCK ALPHA DATA
// Replace with actual AI high-conviction signals
// ============================================

export const createMockAlphaData = (
  direction: "long" | "short" = "long",
  asset: string = "BTC/USDT"
): AlphaData => ({
  direction,
  asset,
  confidence: Math.floor(Math.random() * 10) + 88, // 88-98%
  reason: direction === "long" 
    ? "Strong bullish divergence on RSI with volume confirmation"
    : "Bearish engulfing at key resistance with declining momentum",
});

// ============================================
// MOCK CELEBRATION DATA
// Replace with actual test result data
// ============================================

export const createMockCelebrationData = (
  pnl: number,
  trades?: number,
  winRate?: number
): CelebrationData => ({
  pnl,
  trades: trades ?? Math.floor(Math.random() * 20) + 5,
  winRate: winRate ?? Math.floor(Math.random() * 30) + 60,
});

// ============================================
// DEMO SEQUENCES
// Use these to demo the island animations
// ============================================

export interface IslandDemoSequence {
  type: "narrate" | "trade" | "alpha" | "celebrate" | "connection" | "analyzing" | "idle";
  delay: number; // ms before this event
  data?: NarratorData | TradeData | AlphaData | CelebrationData | ConnectionData | string;
}

/**
 * Demo sequence for backtest start
 */
export const BACKTEST_START_SEQUENCE: IslandDemoSequence[] = [
  { type: "narrate", delay: 0, data: { text: NARRATOR_MESSAGES.backtestStart, type: "info" } },
  { type: "analyzing", delay: 2000, data: NARRATOR_MESSAGES.analyzing },
  { type: "narrate", delay: 4000, data: { text: NARRATOR_MESSAGES.identifyingPatterns, type: "info" } },
];

/**
 * Demo sequence for trade execution
 */
export const TRADE_EXECUTION_SEQUENCE: IslandDemoSequence[] = [
  { type: "narrate", delay: 0, data: { text: NARRATOR_MESSAGES.evaluatingSetup, type: "info" } },
  { type: "alpha", delay: 2000, data: createMockAlphaData("long") },
  { type: "narrate", delay: 5000, data: { text: NARRATOR_MESSAGES.enteringLong, type: "action" } },
  { type: "trade", delay: 6500, data: createMockTradeData("long") },
];

/**
 * Demo sequence for profitable test completion
 */
export const PROFIT_CELEBRATION_SEQUENCE: IslandDemoSequence[] = [
  { type: "narrate", delay: 0, data: { text: NARRATOR_MESSAGES.backtestComplete, type: "result" } },
  { type: "celebrate", delay: 1500, data: createMockCelebrationData(12.4, 8, 75) },
];

/**
 * Demo sequence for connection status
 */
export const CONNECTION_SEQUENCE: IslandDemoSequence[] = [
  { type: "connection", delay: 0, data: { status: "disconnected" } },
  { type: "connection", delay: 3000, data: { status: "reconnecting" } },
  { type: "connection", delay: 5000, data: { status: "connected" } },
];

// ============================================
// SIMULATION HELPERS
// For development/demo purposes
// ============================================

/**
 * Simulates random AI thoughts during a test
 * Replace with actual WebSocket subscription in production
 */
export const getRandomNarratorMessage = (): NarratorData => {
  const messages = [
    { text: NARRATOR_MESSAGES.analyzing, type: "info" as const },
    { text: NARRATOR_MESSAGES.identifyingPatterns, type: "info" as const },
    { text: NARRATOR_MESSAGES.evaluatingSetup, type: "info" as const },
    { text: NARRATOR_MESSAGES.bullishMomentum, type: "info" as const },
    { text: NARRATOR_MESSAGES.bearishPressure, type: "info" as const },
    { text: NARRATOR_MESSAGES.consolidation, type: "info" as const },
    { text: NARRATOR_MESSAGES.waitingForEntry, type: "info" as const },
  ];
  return messages[Math.floor(Math.random() * messages.length)];
};

/**
 * Simulates a trade execution event
 * Replace with actual trade event from backend
 */
export const simulateTradeExecution = (): TradeData => {
  const direction = Math.random() > 0.5 ? "long" : "short";
  const basePrice = 43000 + Math.random() * 500;
  return createMockTradeData(direction, "BTC/USDT", basePrice);
};

/**
 * Simulates an alpha detection event
 * Replace with actual AI signal from backend
 */
export const simulateAlphaDetection = (): AlphaData => {
  const direction = Math.random() > 0.5 ? "long" : "short";
  return createMockAlphaData(direction);
};

// ============================================
// API INTEGRATION TYPES
// Use these when connecting to real backend
// ============================================

export interface IslandEventHandler {
  onNarrate: (data: NarratorData) => void;
  onTradeExecuted: (data: TradeData) => void;
  onAlphaDetected: (data: AlphaData) => void;
  onCelebrate: (data: CelebrationData) => void;
  onConnectionChange: (status: ConnectionData["status"]) => void;
  onAnalyzing: (message?: string) => void;
  onIdle: () => void;
}

/**
 * Placeholder for WebSocket connection
 * Replace with actual WebSocket implementation
 */
export const connectToIslandEvents = (
  _sessionId: string,
  _handlers: IslandEventHandler
): (() => void) => {
  // TODO: Implement WebSocket connection
  // const ws = new WebSocket(`${WS_URL}/island/${sessionId}`);
  // ws.onmessage = (event) => {
  //   const data = JSON.parse(event.data);
  //   switch (data.type) {
  //     case 'narrate': handlers.onNarrate(data.payload); break;
  //     case 'trade': handlers.onTradeExecuted(data.payload); break;
  //     // ... etc
  //   }
  // };
  // return () => ws.close();
  
  return () => {};
};

// ============================================
// LIVE SESSION HELPERS
// Replace with actual session tracking from backend
// ============================================

export interface MockLiveSession {
  id: string;
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

/**
 * Mock function to get active live sessions
 * Replace with actual API call to backend
 */
export const getActiveLiveSessions = (): MockLiveSession[] => {
  // TODO: Replace with actual API call
  // return await fetch('/api/sessions/active').then(r => r.json());
  
  // Demo: Simulating dynamic live session data with realistic updates
  const time = Date.now();
  const variablePnl = 2.3 + Math.sin(time / 10000) * 0.5; // Oscillates between 1.8% and 2.8%
  const hours = Math.floor((time / 1000 / 60 / 60) % 24);
  const minutes = Math.floor((time / 1000 / 60) % 60);
  
  return [{
    id: "session-1",
    agentName: "α-1",
    pnl: Number(variablePnl.toFixed(2)),
    duration: `${hours}h ${minutes}m`,
    status: "running",
    // Rich expanded view data - realistic numbers
    openPositions: 2, // Currently open positions
    totalTrades: 12, // Total trades executed this session
    winRate: 75, // 9 wins out of 12 trades = 75%
    equity: 10234.56 + (variablePnl * 100),
    nextDecisionIn: `${Math.floor(Math.random() * 60) + 15}s`, // 15-75 seconds
  }];
};

/**
 * Check if there are any active live sessions
 */
export const hasActiveLiveSessions = (): boolean => {
  return getActiveLiveSessions().length > 0;
};

/**
 * Get the primary (first) active session for display
 */
export const getPrimaryLiveSession = (): MockLiveSession | null => {
  const sessions = getActiveLiveSessions();
  return sessions.length > 0 ? sessions[0] : null;
};

