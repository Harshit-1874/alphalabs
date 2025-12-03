// Arena Types (Backtest & Forward Test)

export type TestType = "backtest" | "forward";
export type BattleStatus = "configuring" | "running" | "paused" | "completed" | "failed";
export type PlaybackSpeed = "slow" | "normal" | "fast" | "instant";

export interface Asset {
  id: string;
  name: string;
  icon: string;
  available: boolean;
}

export interface Timeframe {
  id: string;
  name: string;
  minutes: number;
}

export interface DatePreset {
  id: string;
  name: string;
  description?: string;
}

export interface BacktestConfig {
  agentId: string;
  asset: string;
  timeframe: string;
  datePreset: string;
  startDate?: string;
  endDate?: string;
  capital: number;
  speed: PlaybackSpeed;
  safetyMode: boolean;
  allowLeverage: boolean;
}

export interface ForwardTestConfig {
  agentId: string;
  asset: string;
  timeframe: string;
  capital: number;
  safetyMode: boolean;
  emailNotifications: boolean;
  autoStopOnLoss: boolean;
}

export interface BattleState {
  sessionId: string;
  status: BattleStatus;
  currentCandle: number;
  totalCandles: number;
  elapsedTime: number;
  currentPnL: number;
  currentEquity: number;
  openPosition: Position | null;
  trades: Trade[];
  aiThoughts: AIThought[];
}

export interface Position {
  type: "long" | "short";
  entryPrice: number;
  size: number;
  leverage: number;
  stopLoss: number;
  takeProfit: number;
  unrealizedPnL: number;
  openedAt: Date;
}

export interface Trade {
  id: string;
  type: "long" | "short";
  entryPrice: number;
  exitPrice: number;
  size: number;
  pnl: number;
  pnlPercent: number;
  entryTime: Date;
  exitTime: Date;
  reasoning: string;
  confidence?: number;
  stopLoss?: number;
  takeProfit?: number;
}

export interface AIThought {
  id: string;
  timestamp: Date;
  candle: number;
  type: "analysis" | "decision" | "execution";
  content: string;
  action?: "long" | "short" | "hold" | "close";
}

export interface LiveSession {
  id: string;
  agentId: string;
  agentName: string;
  asset: string;
  startedAt: Date;
  duration: string;
  pnl: number;
  trades: number;
  winRate: number;
  status: "running" | "paused";
}

