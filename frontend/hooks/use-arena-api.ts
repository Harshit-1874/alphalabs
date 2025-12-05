import { useCallback } from "react";
import { useApiClient } from "@/lib/api";
import type { CandleData } from "@/types";
import type { ForwardStatusResponse } from "@/types/arena";

interface BacktestStartPayload {
  agent_id: string;
  asset: string;
  timeframe: string;
  date_preset?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  starting_capital: number;
  playback_speed: string;
  safety_mode: boolean;
  allow_leverage: boolean;
  decision_mode: "every_candle" | "every_n_candles";
  decision_interval_candles: number;
  indicator_readiness_threshold?: number;
  // Council Mode
  council_mode?: boolean;
  council_models?: string[] | null;
  council_chairman_model?: string | null;
}

interface ForwardStartPayload {
  agent_id: string;
  asset: string;
  timeframe: string;
  starting_capital: number;
  safety_mode: boolean;
  email_notifications: boolean;
  auto_stop_on_loss: boolean;
  auto_stop_loss_pct: number;
  allow_leverage: boolean;
  decision_mode: "every_candle" | "every_n_candles";
  decision_interval_candles: number;
}

interface CandleDto {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface BacktestSessionDto {
  id: string;
  status: string;
  agent_id: string;
  agent_name: string;
  asset: string;
  timeframe: string;
  websocket_url: string;
  date_preset?: string | null;
  playback_speed?: string | null;
  safety_mode: boolean;
  allow_leverage: boolean;
  preview_candles?: CandleDto[] | null;
  decision_mode?: string | null;
  decision_interval_candles?: number | null;
  // Council Mode
  council_mode?: boolean;
  council_models?: string[] | null;
  council_chairman_model?: string | null;
}

interface BacktestSession extends BacktestSessionDto {
  previewCandles?: CandleData[];
}

interface BacktestStartResponse {
  session: BacktestSessionDto;
  message: string;
}

interface ForwardStartResponse {
  session: {
    id: string;
    status: string;
    agent_id: string;
    agent_name: string;
    asset: string;
    timeframe: string;
    websocket_url: string;
  };
  message: string;
}

interface BacktestStatusResponse {
  session: {
    id: string;
    status: string;
    agent_id?: string | null;
    agent_name?: string | null;
    asset?: string | null;
    current_candle: number;
    total_candles: number;
    progress_pct: number;
    elapsed_seconds: number;
    current_equity: number;
    current_pnl_pct: number;
    max_drawdown_pct: number;
    trades_count: number;
    win_rate: number;
    open_position: {
      type: "long" | "short";
      entry_price: number;
      unrealized_pnl: number;
    } | null;
  };
}

const mapPreviewCandles = (preview?: CandleDto[] | null): CandleData[] | undefined => {
  if (!preview || preview.length === 0) return undefined;
  return preview.map((candle) => ({
    time: new Date(candle.timestamp).getTime(),
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
    volume: candle.volume,
  }));
};

interface CleanupResponse {
  message: string;
  deleted_sessions: number;
  stopped_in_memory: number;
  session_type: string;
}

export function useArenaApi() {
  const { post, get, del } = useApiClient();

  const startBacktest = useCallback(
    async (payload: BacktestStartPayload): Promise<BacktestSession> => {
      const response = await post<BacktestStartResponse>("/api/arena/backtest/start", payload);
      return {
        ...response.session,
        previewCandles: mapPreviewCandles(response.session.preview_candles),
      };
    },
    [post]
  );

  const startForwardTest = useCallback(
    async (payload: ForwardStartPayload) => {
      const response = await post<ForwardStartResponse>("/api/arena/forward/start", payload);
      return response.session;
    },
    [post]
  );

  const getBacktestStatus = useCallback(
    async (sessionId: string) => {
      const response = await get<BacktestStatusResponse>(`/api/arena/backtest/${sessionId}`);
      return response.session;
    },
    [get]
  );

  const getBacktestHistory = useCallback(
    async (sessionId: string) => {
      return get<{
        candles: any[];
        thoughts: Array<{
          candle_number: number;
          timestamp: string;
          decision?: string | null;
          reasoning?: string | null;
          indicator_values?: Record<string, number | null>;
          order_data?: any;
          council_stage1?: any;
          council_stage2?: any;
          council_metadata?: any;
        }>;
        trades: any[];
      }>(`/api/arena/backtest/${sessionId}/history`);
    },
    [get]
  );

  const getForwardStatus = useCallback(
    async (sessionId: string) => {
      const response = await get<{ session: ForwardStatusResponse }>(
        `/api/arena/forward/${sessionId}`
      );
      return response.session;
    },
    [get]
  );

  const getForwardHistory = useCallback(
    async (sessionId: string) => {
      return get<{
        candles: any[];
        thoughts: Array<{
          candle_number: number;
          timestamp: string;
          decision?: string | null;
          reasoning?: string | null;
          indicator_values?: Record<string, number | null>;
          order_data?: any;
          council_stage1?: any;
          council_stage2?: any;
          council_metadata?: any;
        }>;
        trades: any[];
      }>(`/api/arena/forward/${sessionId}/history`);
    },
    [get]
  );

  const cleanupActiveSessions = useCallback(
    async (sessionType?: "backtest" | "forward"): Promise<CleanupResponse> => {
      const endpoint = sessionType 
        ? `/api/arena/cleanup?session_type=${sessionType}`
        : "/api/arena/cleanup";
      return await del<CleanupResponse>(endpoint);
    },
    [del]
  );

  return {
    startBacktest,
    startForwardTest,
    getBacktestStatus,
    getBacktestHistory,
    getForwardStatus,
    getForwardHistory,
    cleanupActiveSessions,
  };
}

