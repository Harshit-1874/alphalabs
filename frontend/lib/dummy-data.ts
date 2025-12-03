/**
 * Centralized dummy data for frontend testing
 * All mock data in one place - easy to swap with real API calls later
 */

import type {
  Agent,
  AgentStats,
  DashboardStats,
  ActivityItem,
  QuickStartStep,
  LiveSession,
  TestResult,
  ResultsStats,
  Asset,
  Timeframe,
  DatePreset,
  ApiKey,
  CandleData,
  EquityCurvePoint,
  Trade,
  AIThought,
  Notification,
  UserProfile,
} from "@/types";

// ============================================
// USER DATA
// ============================================

export const DUMMY_USER: UserProfile = {
  id: "user-1",
  email: "alex.verma@gmail.com",
  name: "Alex Verma",
  avatarUrl: "https://api.dicebear.com/7.x/avataaars/svg?seed=alex",
  plan: "pro",
  createdAt: new Date("2025-10-01"),
};

// ============================================
// AGENTS DATA
// ============================================

export const DUMMY_AGENTS: Agent[] = [
  {
    id: "agent-1",
    name: "α-1",
    model: "DeepSeek-R1",
    mode: "monk",
    indicators: ["RSI", "MACD", "EMA", "ATR", "Volume", "Stochastic"],
    customIndicators: [{ name: "Secret_Sauce", formula: "(close - sma_50) / atr_14" }],
    strategyPrompt: `My trading philosophy:

1. Only enter LONG positions when RSI is below 30 (oversold) AND MACD histogram is turning positive (momentum shift).

2. Only enter SHORT positions when RSI is above 70 (overbought) AND price is below EMA_50 (bearish trend).

3. Always set stop loss at 1.5x ATR below entry for LONG, above entry for SHORT.

4. Take profit at 2x the stop loss distance (2:1 R:R).

5. If uncertain, HOLD. Capital preservation is priority.`,
    apiKeyMasked: "sk-or-v1-••••••••",
    testsRun: 12,
    bestPnL: 47.2,
    createdAt: new Date("2025-11-15"),
    updatedAt: new Date("2025-11-24"),
    stats: { totalTests: 12, profitableTests: 8, bestPnL: 47.2, avgWinRate: 58, avgDrawdown: -8.3 },
  },
  {
    id: "agent-2",
    name: "β-2",
    model: "Claude 3.5",
    mode: "omni",
    indicators: ["All Indicators", "News Sentiment"],
    customIndicators: [],
    strategyPrompt: `Omni Mode Strategy: Use all available data including news sentiment to make informed decisions. Focus on high-probability setups with strong confluence.`,
    apiKeyMasked: "sk-or-v1-••••••••",
    testsRun: 8,
    bestPnL: 23.1,
    createdAt: new Date("2025-11-18"),
    updatedAt: new Date("2025-11-22"),
    stats: { totalTests: 8, profitableTests: 3, bestPnL: 23.1, avgWinRate: 52, avgDrawdown: -12.1 },
  },
  {
    id: "agent-3",
    name: "γ-3",
    model: "Gemini 1.5 Pro",
    mode: "monk",
    indicators: ["RSI", "Bollinger Bands", "VWAP"],
    customIndicators: [],
    strategyPrompt: `Mean reversion strategy focusing on oversold/overbought conditions with Bollinger Band confirmation.`,
    apiKeyMasked: "sk-or-v1-••••••••",
    testsRun: 0,
    bestPnL: null,
    createdAt: new Date("2025-11-24"),
    updatedAt: new Date("2025-11-24"),
    stats: { totalTests: 0, profitableTests: 0, bestPnL: 0, avgWinRate: 0, avgDrawdown: 0 },
  },
];

export const DUMMY_AGENT_STATS: Record<string, AgentStats> = {
  "agent-1": { totalTests: 12, profitableTests: 8, bestPnL: 47.2, avgWinRate: 58, avgDrawdown: -8.3 },
  "agent-2": { totalTests: 8, profitableTests: 3, bestPnL: 23.1, avgWinRate: 52, avgDrawdown: -12.1 },
  "agent-3": { totalTests: 0, profitableTests: 0, bestPnL: 0, avgWinRate: 0, avgDrawdown: 0 },
};

// ============================================
// DASHBOARD DATA
// ============================================

export const DUMMY_DASHBOARD_STATS: DashboardStats = {
  totalAgents: 3,
  testsRun: 27,
  bestPnL: 47.2,
  avgWinRate: 62,
  trends: {
    agentsThisWeek: 1,
    testsToday: 5,
    winRateChange: 3,
  },
  bestAgent: "α-1",
};

export const DUMMY_ACTIVITY: ActivityItem[] = [
  {
    id: "act-1",
    type: "test_completed",
    agentName: "α-1",
    description: "Backtest completed",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    pnl: 23.4,
    resultId: "result-27",
  },
  {
    id: "act-2",
    type: "test_failed",
    agentName: "β-2",
    description: "Backtest completed",
    timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000),
    pnl: -5.2,
    resultId: "result-26",
  },
  {
    id: "act-3",
    type: "agent_created",
    agentName: "γ-3",
    description: "Agent created",
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
  },
];

export const DUMMY_QUICK_START: QuickStartStep[] = [
  {
    id: "step-1",
    label: "Create your first agent",
    description: "Configure an AI trading agent",
    isComplete: true,
    href: "/dashboard/agents/new",
    ctaText: "Create",
  },
  {
    id: "step-2",
    label: "Run a backtest",
    description: "Test against historical data",
    isComplete: false,
    href: "/dashboard/arena/backtest",
    ctaText: "Start Test",
  },
  {
    id: "step-3",
    label: "Generate your first certificate",
    description: "Prove your AI's performance",
    isComplete: false,
    href: "/dashboard/results",
    ctaText: "View Results",
  },
];

export const DUMMY_LIVE_SESSIONS: LiveSession[] = [
  {
    id: "session-1",
    agentId: "agent-1",
    agentName: "α-1",
    asset: "BTC/USDT",
    startedAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
    duration: "4h 23m",
    pnl: 2.3,
    trades: 3,
    winRate: 66,
    status: "running",
  },
];

// ============================================
// RESULTS DATA
// ============================================

export const DUMMY_RESULTS: TestResult[] = [
  {
    id: "result-27",
    type: "backtest",
    agentId: "agent-1",
    agentName: "α-1",
    asset: "BTC/USDT",
    mode: "monk",
    date: new Date("2025-11-25"),
    duration: "30 days",
    trades: 45,
    pnl: 23.4,
    winRate: 62,
    maxDrawdown: -4.2,
    sharpeRatio: 1.8,
    profitFactor: 2.1,
  },
  {
    id: "result-26",
    type: "forward",
    agentId: "agent-1",
    agentName: "α-1",
    asset: "BTC/USDT",
    mode: "monk",
    date: new Date("2025-11-23"),
    duration: "48 hours",
    trades: 12,
    pnl: 8.2,
    winRate: 67,
    maxDrawdown: -2.1,
  },
  {
    id: "result-25",
    type: "backtest",
    agentId: "agent-2",
    agentName: "β-2",
    asset: "ETH/USDT",
    mode: "omni",
    date: new Date("2025-11-20"),
    duration: "14 days",
    trades: 28,
    pnl: -5.2,
    winRate: 43,
    maxDrawdown: -8.1,
  },
  {
    id: "result-24",
    type: "backtest",
    agentId: "agent-1",
    agentName: "α-1",
    asset: "BTC/USDT",
    mode: "monk",
    date: new Date("2025-11-18"),
    duration: "30 days",
    trades: 52,
    pnl: 47.2,
    winRate: 58,
    maxDrawdown: -6.3,
    sharpeRatio: 2.4,
    profitFactor: 2.8,
  },
];

export const DUMMY_RESULTS_STATS: ResultsStats = {
  totalTests: 27,
  profitable: 18,
  profitablePercent: 67,
  bestResult: 47.2,
  avgPnL: 8.3,
};

// ============================================
// ARENA CONFIG DATA
// ============================================

export const ASSETS: Asset[] = [
  { id: "btc-usdt", name: "BTC/USDT", icon: "₿", available: true },
  { id: "eth-usdt", name: "ETH/USDT", icon: "Ξ", available: true },
  { id: "sol-usdt", name: "SOL/USDT", icon: "◎", available: true },
  { id: "bnb-usdt", name: "BNB/USDT", icon: "B", available: false },
];

export const TIMEFRAMES: Timeframe[] = [
  { id: "15m", name: "15 Minutes", minutes: 15 },
  { id: "1h", name: "1 Hour", minutes: 60 },
  { id: "4h", name: "4 Hours", minutes: 240 },
  { id: "1d", name: "1 Day", minutes: 1440 },
];

export const DATE_PRESETS: DatePreset[] = [
  { id: "7d", name: "Last 7 days" },
  { id: "30d", name: "Last 30 days" },
  { id: "90d", name: "Last 90 days" },
  { id: "bull", name: "Bull Run", description: "Oct 2023 - Mar 2024" },
  { id: "crash", name: "Crash", description: "Nov 2022 - Jan 2023" },
];

export const PLAYBACK_SPEEDS = [
  { id: "slow", name: "Slow (1s/candle)", ms: 1000 },
  { id: "normal", name: "Normal (500ms/candle)", ms: 500 },
  { id: "fast", name: "Fast (200ms/candle)", ms: 200 },
  { id: "instant", name: "Instant", ms: 0 },
];

// ============================================
// CHART DATA (for demo)
// ============================================

export const generateDummyCandles = (count: number, startPrice = 42000): CandleData[] => {
  const candles: CandleData[] = [];
  let price = startPrice;
  const now = Date.now();
  
  for (let i = count; i > 0; i--) {
    const volatility = 0.02;
    const change = (Math.random() - 0.5) * 2 * volatility;
    const open = price;
    const close = price * (1 + change);
    const high = Math.max(open, close) * (1 + Math.random() * 0.01);
    const low = Math.min(open, close) * (1 - Math.random() * 0.01);
    
    candles.push({
      time: now - i * 60 * 60 * 1000,
      open,
      high,
      low,
      close,
      volume: Math.random() * 1000 + 500,
    });
    
    price = close;
  }
  
  return candles;
};

export const generateDummyEquityCurve = (count: number, startEquity = 10000): EquityCurvePoint[] => {
  const points: EquityCurvePoint[] = [];
  let equity = startEquity;
  let peak = startEquity;
  const now = Date.now();
  
  for (let i = count; i > 0; i--) {
    const change = (Math.random() - 0.4) * 0.03; // Slight upward bias
    equity = equity * (1 + change);
    peak = Math.max(peak, equity);
    const drawdown = ((equity - peak) / peak) * 100;
    
    points.push({
      time: now - i * 60 * 60 * 1000,
      value: equity,
      drawdown,
    });
  }
  
  return points;
};

export const DUMMY_TRADES: Trade[] = [
  {
    id: "trade-1",
    type: "long",
    entryPrice: 42150,
    exitPrice: 43200,
    size: 0.5,
    pnl: 525,
    pnlPercent: 2.49,
    entryTime: new Date("2025-11-25T10:00:00"),
    exitTime: new Date("2025-11-25T14:30:00"),
    reasoning: "RSI oversold, MACD bullish crossover",
    confidence: 87,
    stopLoss: 41520,
    takeProfit: 43410,
  },
  {
    id: "trade-2",
    type: "short",
    entryPrice: 43500,
    exitPrice: 43800,
    size: 0.3,
    pnl: -90,
    pnlPercent: -0.69,
    entryTime: new Date("2025-11-25T16:00:00"),
    exitTime: new Date("2025-11-25T18:00:00"),
    reasoning: "RSI overbought, but stop loss hit",
    confidence: 82,
    stopLoss: 44800,
    takeProfit: 42400,
  },
  {
    id: "trade-3",
    type: "long",
    entryPrice: 43200,
    exitPrice: 44500,
    size: 0.4,
    pnl: 520,
    pnlPercent: 3.01,
    entryTime: new Date("2025-11-26T09:00:00"),
    exitTime: new Date("2025-11-26T15:00:00"),
    reasoning: "Strong support bounce with volume confirmation",
    confidence: 91,
    stopLoss: 42000,
    takeProfit: 45360,
  },
];

export const DUMMY_AI_THOUGHTS: AIThought[] = [
  {
    id: "thought-1",
    timestamp: new Date("2025-11-25T10:00:00"),
    candle: 1,
    type: "analysis",
    content: "RSI at 28 indicates oversold conditions. MACD histogram showing early signs of bullish divergence. Volume increasing on recent candles.",
  },
  {
    id: "thought-2",
    timestamp: new Date("2025-11-25T10:01:00"),
    candle: 1,
    type: "decision",
    content: "Conditions met for LONG entry. RSI < 30 ✓, MACD turning positive ✓. Setting stop loss at 1.5x ATR below entry.",
    action: "long",
  },
  {
    id: "thought-3",
    timestamp: new Date("2025-11-25T14:30:00"),
    candle: 5,
    type: "execution",
    content: "Take profit target reached. Closing position with +2.49% gain.",
    action: "close",
  },
];

// ============================================
// SETTINGS DATA
// ============================================

export const DUMMY_API_KEYS: ApiKey[] = [
  {
    id: "key-1",
    provider: "OpenRouter",
    label: "Default",
    maskedKey: "sk-or-v1-••••••••••••••••••••••",
    addedAt: new Date("2025-11-15"),
    lastUsed: "2 hours ago",
    usedBy: ["α-1", "β-2"],
    status: "valid",
    isDefault: true,
  },
  {
    id: "key-2",
    provider: "OpenRouter",
    label: "Secondary",
    maskedKey: "sk-or-v1-••••••••••••••••••••••",
    addedAt: new Date("2025-11-20"),
    lastUsed: null,
    usedBy: [],
    status: "untested",
    isDefault: false,
  },
];

export const DUMMY_NOTIFICATIONS: Notification[] = [
  {
    id: "notif-1",
    type: "success",
    title: "Backtest Complete",
    message: "α-1 finished backtest with +23.4% PnL",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    read: false,
    actionUrl: "/dashboard/results/result-27",
  },
  {
    id: "notif-2",
    type: "info",
    title: "Forward Test Running",
    message: "α-1 is actively trading BTC/USDT",
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000),
    read: true,
    actionUrl: "/dashboard/arena/forward/session-1",
  },
];

// ============================================
// AI MODELS
// ============================================

export const AI_MODELS = [
  {
    id: "deepseek-r1",
    name: "DeepSeek-R1",
    iconType: "atom",
    description: "Best for: Logical reasoning, math-heavy strategies",
    speed: "Fast",
    context: "64K tokens",
  },
  {
    id: "claude-3.5-sonnet",
    name: "Claude 3.5 Sonnet",
    iconType: "lightning",
    description: "Best for: Nuanced analysis, complex reasoning",
    speed: "Medium",
    context: "200K tokens",
  },
  {
    id: "gemini-1.5-pro",
    name: "Gemini 1.5 Pro",
    iconType: "cpu",
    description: "Best for: Large context, multi-modal analysis",
    speed: "Fast",
    context: "1M tokens",
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    iconType: "bot",
    description: "Best for: General purpose, balanced performance",
    speed: "Medium",
    context: "128K tokens",
  },
];

// ============================================
// INDICATORS
// ============================================

export const INDICATOR_CATEGORIES = [
  {
    name: "Momentum",
    indicators: [
      { id: "rsi", name: "RSI (Relative Strength Index)", description: "Measures overbought/oversold conditions" },
      { id: "stoch", name: "Stochastic Oscillator", description: "Momentum indicator comparing close to price range" },
      { id: "cci", name: "CCI (Commodity Channel Index)", description: "Identifies cyclical trends" },
      { id: "mom", name: "MOM (Momentum)", description: "Rate of price change" },
      { id: "ao", name: "AO (Awesome Oscillator)", description: "Market momentum measurement" },
    ],
  },
  {
    name: "Trend",
    indicators: [
      { id: "macd", name: "MACD", description: "Trend-following momentum indicator" },
      { id: "ema", name: "EMA (Exponential Moving Avg)", description: "Smoothed average, recent prices weighted" },
      { id: "sma", name: "SMA (Simple Moving Avg)", description: "Basic average price over period" },
      { id: "adx", name: "ADX (Average Directional Index)", description: "Measures trend strength" },
      { id: "psar", name: "Parabolic SAR", description: "Identifies potential reversals" },
    ],
  },
  {
    name: "Volatility",
    indicators: [
      { id: "atr", name: "ATR (Average True Range)", description: "Measures market volatility" },
      { id: "bb", name: "Bollinger Bands", description: "Volatility-based envelopes" },
      { id: "kc", name: "Keltner Channels", description: "Volatility-based channels" },
    ],
  },
  {
    name: "Volume",
    indicators: [
      { id: "volume", name: "Volume", description: "Total traded amount" },
      { id: "obv", name: "OBV (On-Balance Volume)", description: "Buying/selling pressure" },
      { id: "vwap", name: "VWAP", description: "Volume weighted average price" },
    ],
  },
];

