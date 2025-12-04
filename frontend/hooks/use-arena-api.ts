import { useCallback } from "react";
import { useApiClient } from "@/lib/api";
import type { CandleData } from "@/types";

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

export function useArenaApi() {
  const { post, get } = useApiClient();

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

  return {
    startBacktest,
    startForwardTest,
    getBacktestStatus,
  };
}

