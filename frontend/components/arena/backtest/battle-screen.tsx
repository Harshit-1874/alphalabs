"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  Play,
  Pause,
  FastForward,
  SkipForward,
  Square,
  TrendingUp,
  TrendingDown,
  Clock,
  DollarSign,
  Target,
  Activity,
  ChevronLeft,
  AlertCircle,
} from "lucide-react";
import { Robot } from "@phosphor-icons/react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

import { ShiftCard } from "@/components/ui/shift-card";
import { cn } from "@/lib/utils";
import { CandlestickChart } from "@/components/charts/candlestick-chart";
import { useAgentsStore, useArenaStore, useDynamicIslandStore, useResultsStore, useGlobalRefresh } from "@/lib/stores";
import { useArenaApi } from "@/hooks/use-arena-api";
import { useBacktestWebSocket, type WebSocketEvent } from "@/hooks/use-backtest-websocket";
import { useResultsApi } from "@/hooks/use-results-api";
import { useApiClient } from "@/lib/api";
import { NARRATOR_MESSAGES } from "@/lib/dummy-island-data";
import { toast } from "sonner";
import { BattleScreenSkeleton, ChartSkeleton, StatsRowSkeleton } from "@/components/ui/skeletons";
import type { CandleData, AIThought, Trade, PlaybackSpeed, TradeMarker } from "@/types";

interface BattleScreenProps {
  sessionId: string;
}

export function BattleScreen({ sessionId }: BattleScreenProps) {
  const router = useRouter();

  // Get config and agents from stores
  const {
    backtestConfig,
    sessionData,
    addCandle,
    addTrade,
    addThought,
    updateSessionStats,
    setActiveSessionId,
    clearActiveSessionId,
  } = useArenaStore();
  const { agents } = useAgentsStore();
  const { triggerRefresh: triggerResultsRefresh } = useResultsStore();
  const { getBacktestStatus } = useArenaApi();
  const { fetchTrades, fetchReasoning } = useResultsApi();
  const { post } = useApiClient();
  const { refreshResults, refreshDashboard } = useGlobalRefresh();

  // Dynamic Island controls
  const {
    showAnalyzing,
    showIdle,
    narrate,
    showTradeExecuted,
    showAlphaDetected,
    celebrate,
    hide,
  } = useDynamicIslandStore();

  // State for session data
  const [sessionStatus, setSessionStatus] = useState<{
    status: string;
    current_candle: number;
    total_candles: number;
    current_equity: number;
    current_pnl_pct: number;
    trades_count: number;
    win_rate: number;
    agent_id?: string | null;
    agent_name?: string | null;
    asset?: string | null;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resultId, setResultId] = useState<string | null>(null);
  
  // Track reconnection loading state
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [hasReceivedData, setHasReceivedData] = useState(false);

  // Get config values with fallbacks
  const initialCapital = backtestConfig?.capital ?? 10000;
  const asset = sessionStatus?.asset || backtestConfig?.asset || "btc-usdt";

  // Get session data from Zustand store
  const currentSessionData = sessionData[sessionId] || {
    candles: [],
    trades: [],
    thoughts: [],
    equity: initialCapital,
    pnl: 0,
    status: "initializing",
    currentCandle: 0,
    totalCandles: 0,
  };

  // Find the selected agent from store
  const agent = useMemo(() => {
    const agentId = sessionStatus?.agent_id || backtestConfig?.agentId;
    if (agentId) {
      return agents.find(a => a.id === agentId) || null;
    }
    return null;
  }, [sessionStatus?.agent_id, backtestConfig?.agentId, agents]);

  // Get agent name - use from store if available, otherwise from API response
  const agentName = agent?.name || sessionStatus?.agent_name || "Unknown Agent";

  // Use data from Zustand store instead of local state
  const candles = currentSessionData.candles;
  const thoughts = currentSessionData.thoughts;
  const trades = currentSessionData.trades;
  const equity = currentSessionData.equity;
  const pnl = currentSessionData.pnl;

  // UI state
  const [isCompactLayout, setIsCompactLayout] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    thoughts: true,
    trades: true,
  });

  const totalCandles = sessionStatus?.total_candles || 0;
  const currentCandle = sessionStatus?.current_candle || 0;
  // Calculate progress, using candles.length as fallback if sessionStatus is not available yet
  const progress = totalCandles > 0 
    ? (currentCandle / totalCandles) * 100 
    : 0;
  const winRate = sessionStatus?.win_rate || (trades.length > 0
    ? Math.round((trades.filter((t) => t.pnl > 0).length / trades.length) * 100)
    : 0);

  // WebSocket event handler with debouncing for performance
  useEffect(() => {
    setActiveSessionId(sessionId);
  }, [sessionId, setActiveSessionId]);

  // Debounce stats updates to reduce re-renders
  const statsUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingStatsRef = useRef<{ equity?: number; pnl?: number } | null>(null);

  const debouncedUpdateStats = useCallback((sessionId: string, stats: { equity?: number; pnl?: number }) => {
    pendingStatsRef.current = { ...pendingStatsRef.current, ...stats };
    
    if (statsUpdateTimeoutRef.current) {
      clearTimeout(statsUpdateTimeoutRef.current);
    }
    
    statsUpdateTimeoutRef.current = setTimeout(() => {
      if (pendingStatsRef.current) {
        updateSessionStats(sessionId, pendingStatsRef.current);
        pendingStatsRef.current = null;
      }
    }, 100); // Debounce stats updates by 100ms
  }, [updateSessionStats]);

  const handleWebSocketEvent = useCallback((event: WebSocketEvent) => {
    switch (event.type) {
      case "candle":
        // Add new candle to chart - store in Zustand
        if (event.data) {
          const idx =
            event.data.candle_index ??
            event.data.candle_number ??
            currentCandle;
          console.log("[Arena] Candle update", {
            sessionId,
            candleIndex: idx,
          });
          const candleData: CandleData = {
            time: new Date(event.data.timestamp).getTime(),
            open: event.data.open,
            high: event.data.high,
            low: event.data.low,
            close: event.data.close,
            volume: event.data.volume,
          };
          addCandle(sessionId, candleData);
        }
        break;

      case "ai_thinking":
        // AI is analyzing - show in dynamic island
        if (event.data?.status === "analyzing") {
          showAnalyzing({
            message: NARRATOR_MESSAGES.analyzing,
            phase: "analyzing",
            currentAsset: asset.toUpperCase().replace("-", "/"),
            sessionId: sessionId,
            sessionType: "backtest",
          });
        }
        break;

      case "ai_decision":
        // AI made a decision - add as thought - store in Zustand
        if (event.data) {
          const candleIndexFromEvent =
            typeof event.data.candle_index === "number" ? event.data.candle_index : currentCandle;
          const councilDeliberation = event.data.decision_context?.council_deliberation;
          const thought: AIThought = {
            id: `thought-${Date.now()}`,
            timestamp: new Date(),
            candle: candleIndexFromEvent,
            type: event.data.action ? "execution" : "decision",
            content: event.data.reasoning || "AI made a decision",
            action: event.data.action?.toLowerCase() as "long" | "short" | "hold" | "close" | undefined,
            decisionMode: event.data.decision_context?.mode,
            decisionInterval:
              typeof event.data.decision_context?.interval === "number"
                ? event.data.decision_context.interval
                : undefined,
            councilDeliberation: councilDeliberation,
          };
          addThought(sessionId, thought);

          // Show in dynamic island if it's a trade decision
          if (event.data.action && event.data.action !== "HOLD") {
            narrate(thought.content, "info");
          }
        }
        break;

      case "position_opened":
        // Position opened - could trigger trade UI update
        if (event.data) {
          narrate(`Position opened: ${event.data.type} at $${event.data.entry_price}`, "info");
        }
        break;

      case "position_closed":
        // Position closed - add to trades - store in Zustand
        if (event.data) {
          const tradeNumber = event.data.trade_number;
          const trade: Trade = {
            id: event.data.id || `trade-${sessionId}-${tradeNumber || Date.now()}`,
            tradeNumber: tradeNumber,
            type: event.data.action?.toLowerCase() === "short" ? "short" : "long",
            entryPrice: event.data.entry_price || 0,
            exitPrice: event.data.exit_price || 0,
            size: event.data.size || 0,
            pnl: event.data.pnl || event.data.pnl_amount || 0,
            pnlPercent: event.data.pnl_pct || 0,
            entryTime: new Date(event.data.entry_time || Date.now()),
            exitTime: new Date(event.data.exit_time || Date.now()),
            reasoning: event.data.reasoning || "",
            confidence: event.data.confidence,
            stopLoss: event.data.stop_loss,
            takeProfit: event.data.take_profit,
          };
          addTrade(sessionId, trade);

          // Show trade executed in dynamic island
          showTradeExecuted({
            direction: trade.type as "long" | "short",
            asset: asset.toUpperCase().replace("-", "/"),
            entryPrice: trade.entryPrice,
            confidence: trade.confidence || 85,
            stopLoss: trade.stopLoss || 0,
            takeProfit: trade.takeProfit || 0,
            reasoning: trade.reasoning,
          });
        }
        break;

      case "stats_update":
        // Stats updated - store in Zustand (debounced)
        if (event.data) {
          debouncedUpdateStats(sessionId, {
            equity: event.data.current_equity,
            pnl: event.data.equity_change_pct,
          });
        }
        break;

      case "session_completed":
        // Session finished - fetch final result
        if (event.data?.result_id) {
          setResultId(event.data.result_id);
          clearActiveSessionId();
          // Trigger refresh of results and dashboard stores so new result appears
          triggerResultsRefresh();
          refreshResults();
          refreshDashboard();
          // Navigate to results page
          setTimeout(() => {
            router.push(`/dashboard/results/${event.data.result_id}`);
          }, 2000);
        }
        break;
    }
  }, [asset, currentCandle, showAnalyzing, narrate, showTradeExecuted, equity, pnl, router, setActiveSessionId, clearActiveSessionId, triggerResultsRefresh, debouncedUpdateStats, addCandle, addTrade, addThought]);

  // Connect to WebSocket
  const { isConnected, sessionState, error: wsError } = useBacktestWebSocket(
    sessionId,
    handleWebSocketEvent
  );
  
  // Detect reconnection state - on mount, if we have no data yet, show reconnecting state
  useEffect(() => {
    if (candles.length === 0 && !hasReceivedData) {
      setIsReconnecting(true);
    }
  }, [candles.length, hasReceivedData]);
  
  // Detect when data has been received
  useEffect(() => {
    // Data is loaded when we have:
    // 1. WebSocket connected
    // 2. Candles received
    // 3. SessionStatus with valid total_candles (not 0)
    const hasData = isConnected && 
                    candles.length > 0 && 
                    sessionStatus !== null && 
                    sessionStatus.total_candles > 0;
    
    if (hasData && (isReconnecting || !hasReceivedData)) {
      setIsReconnecting(false);
      setHasReceivedData(true);
    }
  }, [candles.length, isConnected, sessionStatus, isReconnecting, hasReceivedData]);
  
  // Timeout fallback - if connected but no data after 10 seconds, stop reconnecting
  useEffect(() => {
    if (!isReconnecting || !isConnected) return;
    
    const timeout = setTimeout(() => {
      if (isReconnecting && isConnected) {
        console.log("Data load timeout - showing interface anyway");
        setIsReconnecting(false);
        setHasReceivedData(true);
      }
    }, 10000); // 10 second timeout
    
    return () => clearTimeout(timeout);
  }, [isReconnecting, isConnected]);

  // Memoize previous status to avoid unnecessary updates
  const previousStatusRef = useRef<typeof sessionStatus>(null);

  // Deep equality check for status
  const statusChanged = useCallback((newStatus: typeof sessionStatus, prevStatus: typeof sessionStatus): boolean => {
    if (!prevStatus) return true; // First load
    if (!newStatus) return false;

    // Compare all relevant fields
    return (
      newStatus.status !== prevStatus.status ||
      newStatus.current_candle !== prevStatus.current_candle ||
      newStatus.total_candles !== prevStatus.total_candles ||
      Math.abs(newStatus.current_equity - prevStatus.current_equity) > 0.01 ||
      Math.abs(newStatus.current_pnl_pct - prevStatus.current_pnl_pct) > 0.0001 ||
      newStatus.trades_count !== prevStatus.trades_count ||
      Math.abs(newStatus.win_rate - prevStatus.win_rate) > 0.0001 ||
      newStatus.agent_id !== prevStatus.agent_id ||
      newStatus.agent_name !== prevStatus.agent_name ||
      newStatus.asset !== prevStatus.asset
    );
  }, []);

  // Fetch initial session status - optimized to show UI immediately
  useEffect(() => {
    const fetchInitialStatus = async () => {
      if (!sessionId) return;

      try {
        // Don't block UI - show loading state but allow WebSocket to start
        setIsLoading(true);
        setError(null);

        const status = await getBacktestStatus(sessionId);

        // Only update if status actually changed (memoization)
        if (statusChanged(status, previousStatusRef.current)) {
          previousStatusRef.current = status;
          setSessionStatus(status);
          // Update Zustand store with initial status
          updateSessionStats(sessionId, {
            equity: status.current_equity,
            pnl: status.current_pnl_pct,
            status: status.status,
            currentCandle: status.current_candle,
            totalCandles: status.total_candles,
          });
        }

        // If session is completed, fetch trades and thoughts from results
        if (status.status === "completed") {
          // Try to find result ID - we might need to fetch it from results list
          // For now, we'll rely on WebSocket session_completed event
        }
      } catch (err) {
        console.error("Failed to fetch session status:", err);
        setError(err instanceof Error ? err.message : "Failed to load session");
      } finally {
        // Don't block UI - allow WebSocket data to render even if initial fetch is slow
        setIsLoading(false);
      }
    };

    // Fetch in background, don't block render
    void fetchInitialStatus();

    // Poll for status updates every 10 seconds if not connected via WebSocket (reduced frequency)
    const pollInterval = setInterval(() => {
      if (!isConnected && sessionId) {
        getBacktestStatus(sessionId).then((newStatus) => {
          // Only update if status actually changed (memoization)
          if (statusChanged(newStatus, previousStatusRef.current)) {
            previousStatusRef.current = newStatus;
            setSessionStatus(newStatus);
          }
        }).catch(console.error);
      }
    }, 10000); // Increased from 5s to 10s to reduce load

    return () => clearInterval(pollInterval);
  }, [sessionId, getBacktestStatus, isConnected, updateSessionStats, statusChanged]);

  // Sync WebSocket state with Zustand store
  useEffect(() => {
    if (sessionState) {
      setSessionStatus((prev) => ({
        ...(prev ?? {}),
        status: sessionState.status,
        current_candle: sessionState.currentCandle,
        total_candles: sessionState.totalCandles,
        current_equity: sessionState.currentEquity,
        current_pnl_pct: sessionState.currentPnlPct,
        trades_count: sessionState.tradesCount,
        win_rate: sessionState.winRate,
      } as any));
      // Update Zustand store
      updateSessionStats(sessionId, {
        equity: sessionState.currentEquity,
        pnl: sessionState.currentPnlPct,
        status: sessionState.status,
        currentCandle: sessionState.currentCandle,
        totalCandles: sessionState.totalCandles,
      });
    }
  }, [sessionState, sessionId, updateSessionStats]);

  // Update visible candles based on current progress
  // Sync with backend's currentCandle to ensure chart stays in sync with processing
  const playbackSpeed = backtestConfig?.speed ?? "normal";

  // For instant mode, show all candles immediately
  // For other modes, sync displayCandleCount with backend's currentCandle
  // currentCandle is 0-indexed, so if currentCandle=50, we've processed 51 candles (0-50)
  const displayCandleCount = useMemo(() => {
    if (candles.length === 0) {
      return 0;
    }
    if (playbackSpeed === "instant") {
      return candles.length;
    }
    // Sync with backend's currentCandle (0-indexed, so add 1 for display count)
    // This ensures chart stays in sync with backend processing
    // Cap at candles.length to avoid showing candles that haven't been received yet
    if (currentCandle >= 0) {
      return Math.min(currentCandle + 1, candles.length);
    }
    return 1;
  }, [candles.length, currentCandle, playbackSpeed]);

  const visibleCandles = useMemo(() => {
    if (candles.length === 0) return [];
    const count = playbackSpeed === "instant" ? candles.length : Math.max(displayCandleCount, 1);
    return candles.slice(0, Math.min(count, candles.length));
  }, [candles, displayCandleCount, playbackSpeed]);

  const decisionMarkers: TradeMarker[] = useMemo(() => {
    if (!candles.length || thoughts.length === 0) return [];
    const latestVisibleTime =
      playbackSpeed === "instant"
        ? Infinity
        : visibleCandles[visibleCandles.length - 1]?.time ?? 0;

    const markers: TradeMarker[] = [];

    thoughts.forEach((thought) => {
      if (!thought.action || (thought.action !== "long" && thought.action !== "short")) {
        return;
      }
      const candleAtDecision = candles[thought.candle];
      if (!candleAtDecision) return;
      if (candleAtDecision.time > latestVisibleTime) {
        return;
      }
      const isShort = thought.action === "short";
      markers.push({
        time: candleAtDecision.time,
        position: isShort ? "above" : "below",
        type: isShort ? "entry-short" : "entry-long",
        price: isShort ? candleAtDecision.high : candleAtDecision.low,
        label: thought.action.slice(0, 1).toUpperCase(),
      });
    });

    return markers;
  }, [thoughts, candles, visibleCandles, playbackSpeed]);

  useEffect(() => {
    const handleResize = () => {
      setIsCompactLayout(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    setExpandedSections((prev) => {
      const next = isCompactLayout
        ? { thoughts: false, trades: false }
        : { thoughts: true, trades: true };
      return prev.thoughts === next.thoughts && prev.trades === next.trades ? prev : next;
    });
  }, [isCompactLayout]);

  const handleStop = useCallback(async () => {
    try {
      // If session is already completed, just navigate to result
      if (sessionStatus?.status === "completed" && resultId) {
        router.push(`/dashboard/results/${resultId}`);
        return;
      }

      // If session is still running, call stop API
      if (sessionStatus?.status === "running" || sessionStatus?.status === "paused") {
        const response = await post(`/api/arena/backtest/${sessionId}/stop`, {
          close_position: true,
        }) as { result_id?: string };
        if (response?.result_id) {
          router.push(`/dashboard/results/${response.result_id}`);
        } else {
          router.push("/dashboard/results");
        }
      } else if (resultId) {
        // Session completed, navigate to result
        router.push(`/dashboard/results/${resultId}`);
      } else {
        // Fallback to results list
        router.push("/dashboard/results");
      }
    } catch (err) {
      console.error("Error stopping session:", err);
      toast.error(err instanceof Error ? err.message : "Failed to stop session");
      // Still try to navigate if we have resultId
      if (resultId) {
        router.push(`/dashboard/results/${resultId}`);
      } else {
        router.push("/dashboard/results");
      }
    }
  }, [router, resultId, sessionId, sessionStatus?.status, post]);

  // ============================================
  // DYNAMIC ISLAND TRIGGERS
  // ============================================

  // Track previous PnL for profit crossing detection
  const prevPnlRef = useRef(0);
  const hasShownAlphaRef = useRef(false);
  const lastNarratorCandleRef = useRef(0);

  // Show analyzing when session starts
  useEffect(() => {
    if (sessionStatus?.status === "running" && currentCandle === 0) {
      narrate(NARRATOR_MESSAGES.backtestStart, "info");
    } else if (sessionStatus?.status === "running" && currentCandle > 0) {
      // Check if we're currently showing a trade or alpha (priority states)
      const islandState = useDynamicIslandStore.getState();
      const isPriorityMode = islandState.mode === "trade" || islandState.mode === "alpha" || islandState.mode === "celebration";

      // Only show analyzing if not in a priority state
      if (!isPriorityMode) {
        // Show what AI is doing - phase based on progress
        const phase = progress < 30 ? "scanning" :
          progress < 70 ? "analyzing" : "deciding";
        showAnalyzing({
          message: NARRATOR_MESSAGES.analyzing,
          phase,
          currentAsset: asset.toUpperCase().replace("-", "/"),
          sessionId: sessionId,
          sessionType: "backtest",
        });
      }
    } else if (sessionStatus?.status === "paused" && currentCandle > 0 && progress < 100) {
      showIdle();
    }
  }, [sessionStatus?.status, currentCandle, progress, asset, narrate, showAnalyzing, showIdle]);

  // Track last thought count to show AI thoughts in Dynamic Island
  const lastThoughtCountRef = useRef(0);

  // Show AI thoughts in Dynamic Island when new thoughts are added
  useEffect(() => {
    if (thoughts.length === 0 || sessionStatus?.status !== "running") return;

    // Check if we have a new thought
    if (thoughts.length > lastThoughtCountRef.current) {
      const latestThought = thoughts[0];
      if (latestThought && latestThought.type !== "execution") {
        // Only show non-execution thoughts (execution ones trigger trades)
        // Use narrator to show the thought briefly
        narrate(latestThought.content, "info");
      }
      lastThoughtCountRef.current = thoughts.length;
    }
  }, [thoughts, sessionStatus?.status, narrate]);

  // Celebrate when crossing into profit (REMOVED - only celebrate at end)
  useEffect(() => {
    // Just track the previous PnL, no celebration mid-test
    prevPnlRef.current = pnl;
  }, [pnl]);

  // Celebrate on completion if profitable
  useEffect(() => {
    if (sessionStatus?.status === "completed" && pnl > 0) {
      const completionSummary = {
        text: NARRATOR_MESSAGES.backtestComplete,
        type: "result" as const,
        details: `PnL ${pnl.toFixed(1)}% • Trades ${sessionStatus.trades_count || trades.length} • Win rate ${winRate}%`,
        metrics: [
          { label: "PnL", value: `${pnl.toFixed(1)}%` },
          { label: "Trades", value: `${sessionStatus.trades_count || trades.length}` },
          { label: "Win rate", value: `${winRate}%` },
        ],
      };

      narrate(completionSummary.text, completionSummary.type, completionSummary);

      setTimeout(() => {
        celebrate({
          pnl,
          trades: sessionStatus.trades_count || trades.length,
          winRate,
        });
      }, 2500);
    }
  }, [sessionStatus?.status, sessionStatus?.trades_count, pnl, trades.length, winRate, narrate, celebrate]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      hide();
      // Cleanup debounce timeout
      if (statsUpdateTimeoutRef.current) {
        clearTimeout(statsUpdateTimeoutRef.current);
      }
    };
  }, [hide]);

  const toggleSection = (section: keyof typeof expandedSections) => {
    if (!isCompactLayout) return;
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const showAllThoughts = !isCompactLayout || expandedSections.thoughts;
  const showAllTrades = !isCompactLayout || expandedSections.trades;

  const visibleThoughts = showAllThoughts ? thoughts : thoughts.slice(0, 1);
  const visibleTrades = showAllTrades ? trades : trades.slice(0, 1);

  const hiddenThoughts = Math.max(thoughts.length - visibleThoughts.length, 0);
  const hiddenTrades = Math.max(trades.length - visibleTrades.length, 0);

  // Show skeleton loading state - don't block UI completely
  // WebSocket will start connecting immediately and data will flow in
  // Also show when reconnecting after a refresh
  if ((isLoading && !sessionStatus && candles.length === 0) || isReconnecting) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-120px)] gap-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <div className="relative">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              className="w-16 h-16 border-4 border-border rounded-full border-t-[hsl(var(--brand-flame))]"
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <Activity className="h-6 w-6 text-[hsl(var(--brand-flame))] animate-pulse" />
            </div>
          </div>
          
          <div className="text-center space-y-2">
            <h3 className="text-lg font-semibold">
              {hasReceivedData ? "Reconnecting to your session" : "Connecting to your session"}
            </h3>
            <p className="text-sm text-muted-foreground max-w-md">
              {!isConnected 
                ? "Establishing WebSocket connection..." 
                : hasReceivedData 
                  ? "Loading latest data..." 
                  : "Loading session data..."}
            </p>
            {candles.length > 0 && (
              <div className="flex flex-col items-center gap-1 mt-2">
                <p className="text-xs text-muted-foreground">
                  Received {candles.length} candles...
                </p>
                {sessionStatus && sessionStatus.total_candles > 0 && sessionStatus.current_candle > 0 && (
                  <p className="text-xs font-mono text-muted-foreground">
                    Progress: {sessionStatus.current_candle}/{sessionStatus.total_candles} ({Math.round((sessionStatus.current_candle / sessionStatus.total_candles) * 100)}%)
                  </p>
                )}
              </div>
            )}
          </div>
        </motion.div>
        
        {/* Skeleton cards preview */}
        <div className="w-full max-w-4xl px-4 space-y-3 opacity-50">
          <div className="h-12 bg-card/50 border border-border/50 rounded-lg animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="h-24 bg-card/50 border border-border/50 rounded-lg animate-pulse" />
            <div className="h-24 bg-card/50 border border-border/50 rounded-lg animate-pulse" />
            <div className="h-24 bg-card/50 border border-border/50 rounded-lg animate-pulse" />
          </div>
          <div className="h-[300px] bg-card/50 border border-border/50 rounded-lg animate-pulse" />
        </div>
      </div>
    );
  }

  // Treat API errors as fatal, but WebSocket errors are transient because
  // the hook will auto-reconnect. WS issues are surfaced via the "Offline"
  // badge and console logs instead of a full-screen error.
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-120px)]">
        <Card className="border-destructive/40 bg-destructive/10">
          <CardContent className="p-8 text-center">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="h-8 w-8 text-destructive" />
              <div>
                <p className="text-sm font-medium text-destructive">Error loading session</p>
                <p className="text-xs text-muted-foreground mt-2">{error}</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => router.push("/dashboard/arena/backtest")}>
                Back to Arena
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // If still loading or no sessionStatus yet, show skeleton
  // But allow partial rendering if we have some data from WebSocket
  if ((isLoading || !sessionStatus) && candles.length === 0 && thoughts.length === 0) {
    return <BattleScreenSkeleton />;
  }

  // Only show "agent not found" if we have no agent info at all (neither from store nor API)
  // This allows viewing old sessions even if agent is archived/deleted
  if (!sessionStatus?.agent_id && !sessionStatus?.agent_name && !backtestConfig?.agentId) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-120px)]">
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-8 text-center">
            <p className="text-sm text-muted-foreground">Session data not available</p>
            <Button variant="outline" size="sm" onClick={() => router.push("/dashboard/arena/backtest")} className="mt-4">
              Back to Arena
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const renderThought = (thought: AIThought) => (
    <motion.div
      key={thought.id}
      initial={{ opacity: 0, y: -10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{
        type: "spring",
        stiffness: 400,
        damping: 25,
        mass: 0.5
      }}
      className={cn(
        "rounded-md border p-2.5",
        thought.type === "execution"
          ? "border-[hsl(var(--accent-profit)/0.3)] bg-[hsl(var(--accent-profit)/0.05)]"
          : "border-border/50 bg-muted/10"
      )}
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          {thought.action && (
            <Badge
              className={cn(
                "text-[10px] h-5",
                thought.action === "long" && "bg-[hsl(var(--accent-profit))] text-black",
                thought.action === "short" && "bg-[hsl(var(--accent-red))] text-white",
                thought.action === "hold" && "bg-muted text-muted-foreground"
              )}
            >
              {thought.action.toUpperCase()}
            </Badge>
          )}
          <Badge variant="outline" className="text-[10px] h-5">
            {thought.type}
          </Badge>
        </div>
        <span className="text-[10px] text-muted-foreground font-mono">
          #{thought.candle ?? "—"}
        </span>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{thought.content}</p>

      {thought.councilDeliberation && (
        <div className="mt-2 space-y-2 rounded border border-border/40 bg-muted/10 p-2">
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <Badge variant="outline" className="h-4 text-[9px]">Council</Badge>
            <span>Multi-model decision</span>
          </div>

          {/* Stage 1: Individual responses */}
          {thought.councilDeliberation.stage1?.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-medium text-foreground">Stage 1 • Individual opinions</p>
              <div className="space-y-1">
                {thought.councilDeliberation.stage1.map((resp, idx) => (
                  <div
                    key={`${resp.model}-${idx}`}
                    className="rounded border border-border/40 bg-card/30 px-2 py-1.5"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="secondary" className="h-4 text-[9px]">
                        {resp.model.split("/")[1]?.split(":")[0] || resp.model}
                      </Badge>
                    </div>
                    <p className="text-[10px] text-muted-foreground line-clamp-3">
                      {resp.response || "No response"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stage 2 summary */}
          {thought.councilDeliberation.stage2?.length > 0 && (
            <div className="text-[10px] text-muted-foreground">
              Stage 2 • Rankings collected from {thought.councilDeliberation.stage2.length} model
              {thought.councilDeliberation.stage2.length === 1 ? "" : "s"}
            </div>
          )}

          {/* Stage 3: Chairman decision */}
          {thought.councilDeliberation.stage3 && (
            <div className="text-[10px] text-muted-foreground">
              Stage 3 • Chairman:{" "}
              <Badge variant="outline" className="h-4 text-[9px]">
                {thought.councilDeliberation.stage3.model.split("/")[1]?.split(":")[0] ||
                  thought.councilDeliberation.stage3.model}
              </Badge>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );


  return (
    <div className="flex flex-col min-h-[calc(100vh-120px)] gap-2 sm:gap-3 pb-4">
      {/* Header - Mobile responsive */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        {/* Left: Back + Agent + Stats */}
        <div className="flex items-center gap-2 flex-wrap">
          <Link
            href="/dashboard/arena/backtest"
            className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-card/50 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </Link>
          <span className="font-mono text-xs sm:text-sm font-medium">{agentName}</span>
          {!agent && sessionStatus?.agent_name && (
            <Badge variant="outline" className="text-[10px] h-5">
              Archived
            </Badge>
          )}
          <span className="text-[10px] sm:text-xs text-muted-foreground hidden xs:inline">
            {asset.toUpperCase().replace("-", "/")}
          </span>
          {!isConnected && (
            <Badge variant="outline" className="text-[10px] h-5">
              Offline
            </Badge>
          )}
          <Separator orientation="vertical" className="h-3 hidden sm:block" />
          <div className="flex items-center gap-2 text-[10px] sm:text-xs">
            <span className="font-mono font-bold">${(equity / 1000).toFixed(1)}k</span>
            <span className={cn(
              "font-mono font-bold",
              pnl >= 0 ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))]"
            )}>
              {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}%
            </span>
            <span className="text-muted-foreground hidden sm:inline">
              {sessionStatus?.trades_count || trades.length}T {winRate}%W
            </span>
          </div>
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {sessionStatus?.status === "running" && progress < 100 && (
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  await post(`/api/arena/backtest/${sessionId}/pause`);
                  // Status will be updated via WebSocket
                } catch (err) {
                  console.error("Error pausing:", err);
                  toast.error(err instanceof Error ? err.message : "Failed to pause backtest");
                }
              }}
              className="gap-1 h-7 px-2 text-xs"
            >
              <Pause className="h-3 w-3" />
              <span className="hidden xs:inline">Pause</span>
            </Button>
          )}

          {sessionStatus?.status === "paused" && (
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  await post(`/api/arena/backtest/${sessionId}/resume`);
                  // Status will be updated via WebSocket
                } catch (err) {
                  console.error("Error resuming:", err);
                  toast.error(err instanceof Error ? err.message : "Failed to resume backtest");
                }
              }}
              className="gap-1 h-7 px-2 text-xs"
            >
              <Play className="h-3 w-3" />
              <span className="hidden xs:inline">Resume</span>
            </Button>
          )}

          {sessionStatus?.status === "running" && currentCandle > 0 && progress < 100 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={async () => {
                try {
                  const response = await post(`/api/arena/backtest/${sessionId}/stop`, {
                    close_position: true,
                  }) as { result_id?: string };
                  if (response?.result_id) {
                    router.push(`/dashboard/results/${response.result_id}`);
                  } else {
                    router.push("/dashboard/results");
                  }
                } catch (err) {
                  console.error("Error stopping:", err);
                  toast.error(err instanceof Error ? err.message : "Failed to stop backtest");
                }
              }}
              className="h-7 px-2"
            >
              <Square className="h-3 w-3" />
            </Button>
          )}

          {sessionStatus?.status === "completed" && (
            <Button
              size="sm"
              onClick={() => {
                if (resultId) {
                  router.push(`/dashboard/results/${resultId}`);
                } else {
                  router.push("/dashboard/results");
                }
              }}
              className="h-7 px-2 text-xs bg-[hsl(var(--accent-profit))] text-black hover:bg-[hsl(var(--accent-profit))]/90"
            >
              View Results
            </Button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="flex items-center gap-2">
        <Progress value={progress} className="h-1 sm:h-1.5 flex-1" />
        <div className="flex items-center gap-2 text-[10px] sm:text-xs text-muted-foreground">
          <span>{progress.toFixed(0)}%</span>
          {totalCandles > 0 && (
            <span className="hidden sm:inline">
              ({currentCandle}/{totalCandles})
            </span>
          )}
        </div>
      </div>

      {/* Main Content - Fills remaining space */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_220px] gap-2 sm:gap-3 min-h-0">
        {/* Left Column: Chart + AI Thoughts */}
        <div className="flex flex-col gap-2 sm:gap-3 min-h-0">
          {/* Chart */}
          <Card className="border-border/50 bg-card/30 shrink-0">
            <CardContent className="p-1.5 sm:p-2">
              {visibleCandles.length === 0 ? (
                <ChartSkeleton height={300} />
              ) : (
                <CandlestickChart
                  data={visibleCandles}
                  markers={decisionMarkers}
                  height={300}
                  showVolume
                />
              )}
            </CardContent>
          </Card>

          {/* AI Thoughts - Takes remaining space, limited height on mobile */}
          <Card className="border-border/50 bg-card/30 flex-1 lg:min-h-0 min-h-[200px] lg:max-h-none flex flex-col overflow-hidden">
            <CardHeader className="py-2 px-3 shrink-0">
              <CardTitle className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm">
                  <Robot size={16} weight="duotone" className="text-[hsl(var(--brand-flame))]" />
                  AI Thoughts
                </div>
                <div className="flex items-center gap-1.5">
                  {thoughts.length > 0 && (
                    <span className="text-xs text-muted-foreground">{thoughts.length}</span>
                  )}
                  {isCompactLayout && thoughts.length > 1 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 px-2 text-[10px]"
                      onClick={() => toggleSection("thoughts")}
                    >
                      {showAllThoughts ? "Collapse" : "Expand"}
                    </Button>
                  )}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 pt-0 flex-1 min-h-0 flex flex-col">
              {thoughts.length === 0 ? (
                <div className="flex items-center justify-center flex-1 text-xs text-muted-foreground">
                  <Robot size={16} weight="duotone" className="mr-2 opacity-50" />
                  AI thoughts will appear as it analyzes the market
                </div>
              ) : (
                <>
                  {isCompactLayout ? (
                    <div className="space-y-2">
                      <AnimatePresence mode="popLayout">
                        {visibleThoughts.map(renderThought)}
                      </AnimatePresence>
                    </div>
                  ) : (
                    <ScrollArea className="flex-1">
                      <div className="space-y-2 pr-2">
                        <AnimatePresence mode="popLayout">
                          {visibleThoughts.map(renderThought)}
                        </AnimatePresence>
                      </div>
                    </ScrollArea>
                  )}
                  {isCompactLayout && !showAllThoughts && hiddenThoughts > 0 && (
                    <p className="text-[10px] text-muted-foreground text-center mt-2">
                      +{hiddenThoughts} more AI thoughts
                    </p>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Trade Log - Full height, scroll on mobile */}
        <div className="flex flex-col border border-border/50 rounded-lg bg-card/30 max-h-[400px] lg:max-h-none">
          <div className="px-2 py-1.5 border-b border-border/50 bg-muted/30 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                Trades
              </span>
              <span className="text-[10px] font-mono text-muted-foreground">{trades.length}</span>
            </div>
            {isCompactLayout && trades.length > 1 && (
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-[10px]"
                onClick={() => toggleSection("trades")}
              >
                {showAllTrades ? "Collapse" : "Expand"}
              </Button>
            )}
          </div>

          {/* Trade list - hover for details */}
          {isCompactLayout ? (
            <div className="p-1.5 space-y-1.5">
              {trades.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
                  <Target className="h-4 w-4 mb-1.5 opacity-40" />
                  <p className="text-[10px]">No trades</p>
                </div>
              ) : (
                visibleTrades.map((trade, index) => {
                  const topContent = (
                    <div className={cn(
                      "flex items-center justify-between rounded-t px-2 py-1.5",
                      trade.pnl >= 0
                        ? "bg-[hsl(var(--accent-profit)/0.15)]"
                        : "bg-[hsl(var(--accent-red)/0.15)]"
                    )}>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-bold text-foreground">
                          #{index + 1}
                        </span>
                        <Badge className={cn(
                          "text-[8px] h-4 px-1",
                          trade.type === "long" ? "bg-[hsl(var(--accent-profit))] text-black" : "bg-[hsl(var(--accent-red))] text-white"
                        )}>
                          {trade.type === "long" ? "L" : "S"}
                        </Badge>
                      </div>
                      <span className={cn(
                        "font-mono text-sm font-bold",
                        trade.pnl >= 0 ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))]"
                      )}>
                        {trade.pnl >= 0 ? "+" : ""}{trade.pnlPercent}%
                      </span>
                    </div>
                  );

                  const middleContent = (
                    <div className="px-2 py-1 text-center">
                      <p className="font-mono text-[10px] text-muted-foreground">Entry</p>
                      <p className="font-mono text-xs font-medium">${(trade.entryPrice / 1000).toFixed(1)}k</p>
                    </div>
                  );

                  const bottomContent = (
                    <div className={cn(
                      "px-2 pb-2 pt-1 space-y-1.5 border-t",
                      trade.pnl >= 0
                        ? "bg-[hsl(var(--accent-profit)/0.05)] border-[hsl(var(--accent-profit)/0.2)]"
                        : "bg-[hsl(var(--accent-red)/0.05)] border-[hsl(var(--accent-red)/0.2)]"
                    )}>
                      <div className="grid grid-cols-2 gap-1.5">
                        <div className="rounded border border-border/50 bg-muted/20 p-1.5">
                          <p className="text-[9px] text-muted-foreground">Exit</p>
                          <p className="font-mono text-[10px] font-medium">${(trade.exitPrice / 1000).toFixed(1)}k</p>
                        </div>
                        <div className="rounded border border-border/50 bg-muted/20 p-1.5">
                          <p className="text-[9px] text-muted-foreground">Size</p>
                          <p className="font-mono text-[10px] font-medium">0.5 BTC</p>
                        </div>
                      </div>
                      <div className={cn(
                        "rounded p-1.5 text-center",
                        trade.pnl >= 0
                          ? "bg-[hsl(var(--accent-profit)/0.15)]"
                          : "bg-[hsl(var(--accent-red)/0.15)]"
                      )}>
                        <p className="text-[9px] text-muted-foreground">P/L</p>
                        <p className={cn(
                          "font-mono text-xs font-bold",
                          trade.pnl >= 0 ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))]"
                        )}>
                          {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  );

                  return (
                    <ShiftCard
                      key={trade.id}
                      className={cn(
                        "border",
                        trade.pnl >= 0
                          ? "border-[hsl(var(--accent-profit)/0.3)]"
                          : "border-[hsl(var(--accent-red)/0.3)]"
                      )}
                      topContent={topContent}
                      middleContent={middleContent}
                      bottomContent={bottomContent}
                    />
                  );
                })
              )}
            </div>
          ) : (
            <ScrollArea className="flex-1">
              <div className="p-1.5 space-y-1.5">
                {trades.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
                    <Target className="h-4 w-4 mb-1.5 opacity-40" />
                    <p className="text-[10px]">No trades</p>
                  </div>
                ) : (
                  visibleTrades.map((trade, index) => {
                    const tradeNumber = trade.tradeNumber ?? index + 1;
                    const formattedPnl = trade.pnlPercent.toFixed(2);

                    const topContent = (
                      <div className={cn(
                        "flex items-center justify-between rounded-t px-2 py-1.5",
                        trade.pnl >= 0
                          ? "bg-[hsl(var(--accent-profit)/0.15)]"
                          : "bg-[hsl(var(--accent-red)/0.15)]"
                      )}>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-xs font-bold text-foreground">
                            #{tradeNumber}
                          </span>
                          <Badge className={cn(
                            "text-[8px] h-4 px-1",
                            trade.type === "long" ? "bg-[hsl(var(--accent-profit))] text-black" : "bg-[hsl(var(--accent-red))] text-white"
                          )}>
                            {trade.type === "long" ? "L" : "S"}
                          </Badge>
                        </div>
                        <span className={cn(
                          "font-mono text-sm font-bold",
                          trade.pnl >= 0 ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))]"
                        )}>
                          {trade.pnl >= 0 ? "+" : ""}{formattedPnl}%
                        </span>
                      </div>
                    );

                    const middleContent = (
                      <div className="px-2 py-1 text-center">
                        <p className="font-mono text-[10px] text-muted-foreground">Entry</p>
                        <p className="font-mono text-xs font-medium">${(trade.entryPrice / 1000).toFixed(1)}k</p>
                      </div>
                    );

                    const bottomContent = (
                      <div className={cn(
                        "px-2 pb-2 pt-1 space-y-1.5 border-t",
                        trade.pnl >= 0
                          ? "bg-[hsl(var(--accent-profit)/0.05)] border-[hsl(var(--accent-profit)/0.2)]"
                          : "bg-[hsl(var(--accent-red)/0.05)] border-[hsl(var(--accent-red)/0.2)]"
                      )}>
                        <div className="grid grid-cols-2 gap-1.5">
                          <div className="rounded border border-border/50 bg-muted/20 p-1.5">
                            <p className="text-[9px] text-muted-foreground">Exit</p>
                            <p className="font-mono text-[10px] font-medium">${(trade.exitPrice / 1000).toFixed(1)}k</p>
                          </div>
                          <div className="rounded border border-border/50 bg-muted/20 p-1.5">
                            <p className="text-[9px] text-muted-foreground">Size</p>
                            <p className="font-mono text-[10px] font-medium">
                              {trade.size > 0 ? trade.size.toFixed(4) : "—"}
                            </p>
                          </div>
                        </div>
                        <div className={cn(
                          "rounded p-1.5 text-center",
                          trade.pnl >= 0
                            ? "bg-[hsl(var(--accent-profit)/0.15)]"
                            : "bg-[hsl(var(--accent-red)/0.15)]"
                        )}>
                          <p className="text-[9px] text-muted-foreground">P/L</p>
                          <p className={cn(
                            "font-mono text-xs font-bold",
                            trade.pnl >= 0 ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))]"
                          )}>
                            {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
                          </p>
                        </div>
                      </div>
                    );

                    return (
                      <ShiftCard
                        key={trade.id}
                        className={cn(
                          "border",
                          trade.pnl >= 0
                            ? "border-[hsl(var(--accent-profit)/0.3)]"
                            : "border-[hsl(var(--accent-red)/0.3)]"
                        )}
                        topContent={topContent}
                        middleContent={middleContent}
                        bottomContent={bottomContent}
                      />
                    );
                  })
                )}
              </div>
            </ScrollArea>
          )}
          {isCompactLayout && !showAllTrades && hiddenTrades > 0 && (
            <p className="text-[10px] text-muted-foreground text-center pb-2">
              +{hiddenTrades} more trades
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

