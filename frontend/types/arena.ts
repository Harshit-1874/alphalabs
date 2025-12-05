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
  decisionMode: "every_candle" | "every_n_candles";
  decisionIntervalCandles: number;
  // Council Mode - IMPORTANT: councilModels are ADDITIONAL models (bot's model auto-included as first member)
  councilMode?: boolean;
  councilModels?: string[];  // Additional models to join the bot's model
  councilChairmanModel?: string;  // Chairman model (defaults to bot's model if empty)
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
  tradeNumber?: number; // Trade number from backend for deduplication
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
  decisionMode?: "every_candle" | "every_n_candles";
  decisionInterval?: number;
  // Council deliberation data
  councilDeliberation?: CouncilDeliberation;
}

// Council Mode Types
export interface CouncilConfig {
  enabled: boolean;
  models: string[];
  chairmanModel: string;
}

export interface CouncilStage1Response {
  model: string;
  response: string;
}

export interface CouncilStage2Response {
  model: string;
  ranking: string;
  parsed_ranking?: string[];
}

export interface CouncilStage3Response {
  model: string;
  response: string;
}

export interface CouncilAggregateRanking {
  model: string;
  average_rank: number;
  rankings_count: number;
}

export interface CouncilDeliberation {
  stage1: CouncilStage1Response[];
  stage2: CouncilStage2Response[];
  stage3: CouncilStage3Response;
  aggregate_rankings: CouncilAggregateRanking[];
  label_to_model: Record<string, string>;
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

export interface ForwardStatusResponse {
  id: string;
  status: "running" | "paused" | "completed" | "initializing";
  started_at?: string | null;
  elapsed_seconds: number;
  asset: string;
  timeframe: string;
  current_equity: number;
  current_pnl_pct: number;
  max_drawdown_pct: number;
  trades_count: number;
  win_rate: number;
  next_candle_eta?: number | null;
  open_position?: {
    type: "long" | "short";
    entry_price: number;
    unrealized_pnl: number;
  } | null;
}

