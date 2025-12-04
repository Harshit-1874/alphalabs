"use client";

import { useCallback } from "react";
import { usePathname } from "next/navigation";
import { useBacktestWebSocket, type WebSocketEvent } from "@/hooks/use-backtest-websocket";
import { useArenaStore, useDynamicIslandStore } from "@/lib/stores";
import { NARRATOR_MESSAGES } from "@/lib/dummy-island-data";
import type { AIThought, Trade } from "@/types";

export function GlobalBacktestStream() {
  const pathname = usePathname();
  const sessionId = useArenaStore((state) => state.activeSessionId);
  const isBattlePage = pathname.startsWith("/dashboard/arena/backtest/");
  const shouldConnect = Boolean(sessionId) && !isBattlePage;

  const addCandle = useArenaStore((state) => state.addCandle);
  const addTrade = useArenaStore((state) => state.addTrade);
  const addThought = useArenaStore((state) => state.addThought);
  const updateSessionStats = useArenaStore((state) => state.updateSessionStats);
  const upsertLiveBacktest = useArenaStore((state) => state.upsertLiveBacktest);
  const backtestConfig = useArenaStore((state) => state.backtestConfig);

  const {
    showAnalyzing,
    showTradeExecuted,
    narrate,
  } = useDynamicIslandStore();
  const clearActiveSessionId = useArenaStore((state) => state.clearActiveSessionId);

  const handleEvent = useCallback(
    (event: WebSocketEvent) => {
      if (!sessionId) return;
      const { sessionData } = useArenaStore.getState();
      const session = sessionData[sessionId];
      const assetSymbol = backtestConfig?.asset ?? "btc-usdt";

      switch (event.type) {
        case "candle":
          if (event.data) {
            addCandle(sessionId, {
              time: new Date(event.data.timestamp).getTime(),
              open: event.data.open,
              high: event.data.high,
              low: event.data.low,
              close: event.data.close,
              volume: event.data.volume,
            });
            upsertLiveBacktest({
              id: sessionId,
              asset: assetSymbol,
              status: session?.status || "running",
              startedAt: session?.startedAt ? new Date(session.startedAt) : new Date(),
              pnl: session?.pnl || 0,
              progress:
                session?.totalCandles
                  ? ((event.data.candle_index ?? 0) / session.totalCandles) * 100
                  : 0,
            });
          }
          break;

        case "ai_thinking":
          if (event.data?.status === "analyzing") {
            showAnalyzing({
              message: NARRATOR_MESSAGES.analyzing,
              phase: "analyzing",
              currentAsset: assetSymbol.toUpperCase().replace("-", "/"),
            });
          }
          break;

        case "ai_decision":
          if (event.data) {
            const candleIndex =
              typeof event.data.candle_index === "number"
                ? event.data.candle_index
                : session?.currentCandle ?? 0;
            const thought: AIThought = {
              id: `thought-${sessionId}-${Date.now()}`,
              timestamp: new Date(),
              candle: candleIndex,
              type: event.data.action ? "execution" : "decision",
              content: event.data.reasoning || "AI made a decision",
              action: event.data.action?.toLowerCase() as "long" | "short" | "hold" | "close" | undefined,
              decisionMode: event.data.decision_context?.mode,
              decisionInterval:
                typeof event.data.decision_context?.interval === "number"
                  ? event.data.decision_context.interval
                  : undefined,
            };
            addThought(sessionId, thought);

            if (event.data.action && event.data.action !== "HOLD") {
              showTradeExecuted({
                direction: thought.action === "short" ? "short" : "long",
                asset: assetSymbol.toUpperCase().replace("-", "/"),
                entryPrice: event.data.entry_price || event.data.price || 0,
                confidence: 90,
                stopLoss: event.data.stop_loss_price || 0,
                takeProfit: event.data.take_profit_price || 0,
                reasoning: thought.content,
              });
              narrate(thought.content, "info");
            }
          }
          break;

        case "position_opened":
          if (event.data) {
            showTradeExecuted({
              direction: event.data.type?.toLowerCase() === "short" ? "short" : "long",
              asset: assetSymbol.toUpperCase().replace("-", "/"),
              entryPrice: event.data.entry_price || 0,
              confidence: 90,
              stopLoss: event.data.stop_loss || 0,
              takeProfit: event.data.take_profit || 0,
              reasoning: event.data.reasoning || "Position opened",
            });
          }
          break;

        case "position_closed":
          if (event.data) {
            const tradeNumber = event.data.trade_number;
            const trade: Trade = {
              id: event.data.id || `trade-${sessionId}-${tradeNumber || Date.now()}`,
              tradeNumber,
              type: event.data.action?.toLowerCase() === "short" ? "short" : "long",
              entryPrice: event.data.entry_price || 0,
              exitPrice: event.data.exit_price || 0,
              size: event.data.size || 0,
              pnl: event.data.pnl || event.data.pnl_amount || 0,
              pnlPercent: event.data.pnl_pct || 0,
              entryTime: new Date(event.data.entry_time || Date.now()),
              exitTime: new Date(event.data.exit_time || Date.now()),
              reasoning: event.data.reason || "",
              confidence: 85,
              stopLoss: event.data.stop_loss,
              takeProfit: event.data.take_profit,
            };
            addTrade(sessionId, trade);
          }
          break;

        case "stats_update":
          if (event.data) {
            updateSessionStats(sessionId, {
              equity: event.data.current_equity,
              pnl: event.data.equity_change_pct,
              status: event.data.status,
              currentCandle: event.data.current_candle,
              totalCandles: event.data.total_candles,
            });
            upsertLiveBacktest({
              id: sessionId,
              asset: assetSymbol,
              status: event.data.status || "running",
              startedAt: session?.startedAt ? new Date(session.startedAt) : new Date(),
              pnl: event.data.equity_change_pct || 0,
              progress:
                event.data.total_candles > 0
                  ? (event.data.current_candle / event.data.total_candles) * 100
                  : 0,
            });
          }
          break;

        case "session_completed":
          clearActiveSessionId();
          break;
      }
    },
    [sessionId, addCandle, addTrade, addThought, updateSessionStats, backtestConfig, showAnalyzing, showTradeExecuted, narrate, upsertLiveBacktest, clearActiveSessionId]
  );

  useBacktestWebSocket(shouldConnect ? sessionId ?? null : null, shouldConnect ? handleEvent : undefined);

  return null;
}

