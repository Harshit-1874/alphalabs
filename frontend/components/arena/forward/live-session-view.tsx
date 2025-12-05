"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronLeft,
  Square,
  TrendingUp,
  TrendingDown,
  Clock,
  DollarSign,
  Target,
  Activity,
  Wifi,
  WifiOff,
  Bell,
  RefreshCw,
} from "lucide-react";
import { Robot } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ShiftCard } from "@/components/ui/shift-card";
import { cn } from "@/lib/utils";
import { CandlestickChart } from "@/components/charts/candlestick-chart";
import { useApiClient } from "@/lib/api";
import { useArenaApi } from "@/hooks/use-arena-api";
import { useForwardWebSocket, WebSocketEvent } from "@/hooks/use-forward-websocket";
import { useAgentsStore, useArenaStore, useDynamicIslandStore } from "@/lib/stores";
import { websocketManager } from "@/lib/websocket-manager";
// Removed dummy island data imports - using real WebSocket events instead
import type { CandleData, Trade, Position, AIThought as AIThoughtType } from "@/types";
import type { ForwardStatusResponse } from "@/types/arena";

interface LiveSessionViewProps {
  sessionId: string;
}

export function LiveSessionView({ sessionId }: LiveSessionViewProps) {
  // Get config and agents from stores
  const { forwardConfig } = useArenaStore();
  const { agents } = useAgentsStore();
  const { post } = useApiClient();
  const { getForwardStatus } = useArenaApi();
  const router = useRouter();
  
  const [sessionStats, setSessionStats] = useState<ForwardStatusResponse | null>(null);
  const [candlesState, setCandlesState] = useState<CandleData[]>([]);
  const [tradesState, setTradesState] = useState<Trade[]>([]);
  const [thoughtsState, setThoughtsState] = useState<AIThoughtType[]>([]);
  const [positionsState, setPositionsState] = useState<Position[]>([]);
  const [runningTimeState, setRunningTimeState] = useState("–");
  const [nextDecisionState, setNextDecisionState] = useState<number | null>(null);
  const [nextAIDecisionState, setNextAIDecisionState] = useState<number | null>(null);
  const [isPausedState, setIsPausedState] = useState(false);
  const [isConnectedState, setIsConnectedState] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isStopped, setIsStopped] = useState(false);
  const [forwardError, setForwardError] = useState<string | null>(null);
  const [stopError, setStopError] = useState<string | null>(null);
  
  // Track loading state for reconnection
  const [isLoadingHistoricalData, setIsLoadingHistoricalData] = useState(true);
  const [hasReceivedInitialData, setHasReceivedInitialData] = useState(false);
  
  // Track last price to avoid unnecessary updates
  const lastPriceRef = useRef<number | null>(null);

  const activeCandles = candlesState;
  const activeTrades = tradesState;
  const activeThoughts = thoughtsState;
  const activePositions = positionsState;
  const activeRunningTime = runningTimeState;
  const activeNextDecision = nextDecisionState;
  const activeNextAIDecision = nextAIDecisionState;

  const formatRunningTime = (seconds: number) => {
    if (!seconds || seconds <= 0) {
      return "0s";
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours) return `${hours}h ${minutes}m`;
    if (minutes) return `${minutes}m`;
    return `${seconds}s`;
  };

  // Memoize previous status to avoid unnecessary updates
  const previousStatusRef = useRef<ForwardStatusResponse | null>(null);

  // Deep equality check for forward status
  const statusChanged = useCallback((newStatus: ForwardStatusResponse, prevStatus: ForwardStatusResponse | null): boolean => {
    if (!prevStatus) return true; // First load
    
    return (
      newStatus.status !== prevStatus.status ||
      newStatus.elapsed_seconds !== prevStatus.elapsed_seconds ||
      Math.abs(newStatus.current_equity - prevStatus.current_equity) > 0.01 ||
      Math.abs(newStatus.current_pnl_pct - prevStatus.current_pnl_pct) > 0.0001 ||
      newStatus.trades_count !== prevStatus.trades_count ||
      Math.abs(newStatus.win_rate - prevStatus.win_rate) > 0.0001 ||
      newStatus.next_candle_eta !== prevStatus.next_candle_eta ||
      newStatus.asset !== prevStatus.asset ||
      (newStatus.open_position?.type !== prevStatus.open_position?.type) ||
      (newStatus.open_position?.entry_price !== prevStatus.open_position?.entry_price) ||
      (Math.abs((newStatus.open_position?.unrealized_pnl ?? 0) - (prevStatus.open_position?.unrealized_pnl ?? 0)) > 0.01)
    );
  }, []);

  const fetchSessionStatus = useCallback(async () => {
    setForwardError(null);
    try {
      const status = await getForwardStatus(sessionId);
      
      // Only update if status actually changed (memoization)
      if (statusChanged(status, previousStatusRef.current)) {
        previousStatusRef.current = status;
        setSessionStats(status);
        setIsPausedState(status.status === "paused");
        setRunningTimeState(formatRunningTime(status.elapsed_seconds));
        setNextDecisionState(status.next_candle_eta ?? null);
        if (status.open_position) {
          setPositionsState([
            {
              type: status.open_position.type,
              entryPrice: status.open_position.entry_price,
              size: 0,
              leverage: 1,
              stopLoss: 0,
              takeProfit: 0,
              unrealizedPnL: status.open_position.unrealized_pnl,
              openedAt: new Date(),
            },
          ]);
        } else {
          setPositionsState([]);
        }
      }
    } catch (err) {
      setForwardError(err instanceof Error ? err.message : "Failed to load forward session");
    }
  }, [getForwardStatus, sessionId, statusChanged, formatRunningTime]);

  // Get the actual asset from session stats or fallback to config
  const displayAsset = useMemo(() => {
    if (sessionStats?.asset) {
      return sessionStats.asset.toUpperCase().replace("-", "/");
    }
    if (forwardConfig?.asset) {
      return forwardConfig.asset.toUpperCase().replace("-", "/");
    }
    return "BTC/USDT";
  }, [sessionStats?.asset, forwardConfig?.asset]);

  useEffect(() => {
    void fetchSessionStatus();
  }, [fetchSessionStatus]);

  // Debounce state updates to prevent "bomb" effect
  const updateQueueRef = useRef<Array<() => void>>([]);
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const flushUpdates = useCallback(() => {
    if (updateQueueRef.current.length === 0) return;
    const updates = [...updateQueueRef.current];
    updateQueueRef.current = [];
    updates.forEach(update => update());
  }, []);

  const scheduleUpdate = useCallback((updateFn: () => void) => {
    updateQueueRef.current.push(updateFn);
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }
    // Batch updates every 50ms to prevent "bomb" effect
    updateTimeoutRef.current = setTimeout(flushUpdates, 50);
  }, [flushUpdates]);

  const handleForwardEvent = useCallback(
    (event: WebSocketEvent) => {
      switch (event.type) {
        case "session_initialized": {
          console.log("Session initialized:", event.data);
          // Session is ready, update status immediately (not batched)
          if (event.data) {
            setSessionStats((prev) => ({
              ...(prev ?? {
                id: sessionId,
                status: "running",
                started_at: new Date().toISOString(),
                elapsed_seconds: 0,
                asset: forwardConfig?.asset ?? "btc-usdt",
                timeframe: forwardConfig?.timeframe ?? "1h",
                current_equity: initialCapital,
                current_pnl_pct: 0,
                max_drawdown_pct: 0,
                trades_count: 0,
                win_rate: 0,
                next_candle_eta: null,
                open_position: null,
              }),
              status: "running",
            }));
          }
          break;
        }
        case "candle": {
          if (!event.data) {
            console.warn("Candle event received but data is missing", event);
            break;
          }
          try {
            const candle: CandleData = {
              time: new Date(event.data.timestamp).getTime(),
              open: event.data.open,
              high: event.data.high,
              low: event.data.low,
              close: event.data.close,
              volume: event.data.volume,
            };
            // Batch candle updates to prevent "bomb" effect
            scheduleUpdate(() => {
              setCandlesState((prev) => {
                // Check if candle with same timestamp already exists (avoid duplicates)
                const existingIndex = prev.findIndex(c => c.time === candle.time);
                if (existingIndex >= 0) {
                  // Update existing candle instead of adding duplicate
                  const updated = [...prev];
                  updated[existingIndex] = candle;
                  return updated;
                }
                // Add new candle
                const updated = [...prev, candle];
                // Sort by time to ensure ascending order
                updated.sort((a, b) => a.time - b.time);
                // Keep last 500 candles (not just 100) to show more history
                return updated.slice(-500);
              });
            });
          } catch (err) {
            console.error("Error processing candle event:", err, event.data);
          }
          break;
        }
        case "price_update": {
          // Real-time price update - update the last candle's close price
          if (!event.data?.price) break;
          try {
            const currentPrice = event.data.price;
            const timestamp = event.data.timestamp ? new Date(event.data.timestamp).getTime() : Date.now();
            
            // Skip if price hasn't changed (avoid unnecessary re-renders)
            if (lastPriceRef.current === currentPrice) {
              break;
            }
            
            lastPriceRef.current = currentPrice;
            
            setCandlesState((prev) => {
              if (prev.length === 0) {
                // No historical candles yet - create a new live candle
                // This ensures the chart starts showing data immediately
                return [{
                  time: timestamp,
                  open: currentPrice,
                  high: currentPrice,
                  low: currentPrice,
                  close: currentPrice,
                  volume: 0,
                }];
              }
              
              const lastCandle = prev[prev.length - 1];
              
              // Skip update if price hasn't actually changed
              if (lastCandle.close === currentPrice && 
                  lastCandle.high >= currentPrice && 
                  lastCandle.low <= currentPrice) {
                return prev;
              }
              
              // Update the last candle with new price (keep same timestamp to avoid duplicates)
              // Create a new array to ensure React detects the change
              const updated = prev.map((candle, idx) => {
                if (idx === prev.length - 1) {
                  // Update the last candle
                  return {
                    ...candle,
                    high: Math.max(candle.high, currentPrice),
                    low: Math.min(candle.low, currentPrice),
                    close: currentPrice,
                  };
                }
                return candle;
              });
              
              return updated;
            });
          } catch (err) {
            console.error("Error processing price update:", err, event.data);
          }
          break;
        }
        case "stats_update": {
          if (!event.data) break;
          setSessionStats((prev) => ({
            ...(prev ?? {
              id: sessionId,
              status: "running",
              started_at: new Date().toISOString(),
              elapsed_seconds: 0,
              asset: forwardConfig?.asset ?? "btc-usdt",
              timeframe: forwardConfig?.timeframe ?? "1h",
              current_equity: initialCapital,
              current_pnl_pct: 0,
              max_drawdown_pct: 0,
              trades_count: 0,
              win_rate: 0,
              next_candle_eta: null,
              open_position: null,
            }),
            current_equity: event.data.current_equity ?? prev?.current_equity ?? 0,
            current_pnl_pct: event.data.equity_change_pct ?? prev?.current_pnl_pct ?? 0,
            trades_count: event.data.total_trades ?? prev?.trades_count ?? 0,
            win_rate: event.data.win_rate ?? prev?.win_rate ?? 0,
            status: event.data.status ?? prev?.status ?? "running",
            max_drawdown_pct: event.data.max_drawdown_pct ?? prev?.max_drawdown_pct ?? 0,
          }));
          setRunningTimeState(
            formatRunningTime(event.data.elapsed_seconds ?? 0)
          );
          if (event.data.current_pnl_pct !== undefined) {
            showAnalyzing({
              message: "Monitoring real-time market conditions...",
              phase: "analyzing",
              currentAsset: displayAsset,
              sessionId: sessionId,
              sessionType: "forward",
            });
          }
          break;
        }
        case "ai_thinking":
          showAnalyzing({
            message: event.data?.text ?? "Analyzing market structure...",
            phase: "analyzing",
            currentAsset: displayAsset,
            sessionId: sessionId,
            sessionType: "forward",
          });
          break;
        case "ai_decision": {
          // Create unique ID based on candle_number to prevent duplicates
          const candleNumber = event.data?.candle_number ?? 0;
          const thoughtId = `thought-${candleNumber}`;
          const reasoning = event.data?.reasoning ?? "AI decision";
          
          // Batch thought updates
          scheduleUpdate(() => {
            setThoughtsState((prev) => {
              const exists = prev.some(t => t.id === thoughtId);
              if (exists) {
                return prev;
              }
              
              const thought: AIThoughtType = {
                id: thoughtId,
                timestamp: new Date(),
                candle: candleNumber,
                type: event.data?.action ? "execution" : "decision",
                content: reasoning,
                action: event.data?.action?.toLowerCase() as AIThoughtType["action"],
              };
              return [thought, ...prev].slice(0, 50);
            });
          });
          
          if (event.data?.action && event.data?.action !== "HOLD") {
            showTradeExecuted({
              direction: event.data.action?.toLowerCase() === "short" ? "short" : "long",
              asset: displayAsset,
              entryPrice: event.data.entry_price ?? 0,
              confidence: 90,
              stopLoss: event.data.stop_loss_price ?? 0,
              takeProfit: event.data.take_profit_price ?? 0,
              reasoning: reasoning,
            });
          }
          break;
        }
        case "position_opened": {
          if (!event.data) break;
          const position: Position = {
            type: event.data.action?.toLowerCase() === "short" ? "short" : "long",
            entryPrice: event.data.entry_price ?? 0,
            size: event.data.size ?? 0,
            leverage: event.data.leverage ?? 1,
            stopLoss: event.data.stop_loss ?? 0,
            takeProfit: event.data.take_profit ?? 0,
            unrealizedPnL: 0,
            openedAt: new Date(event.data.entry_time ?? Date.now()),
          };
          scheduleUpdate(() => {
            setPositionsState((prev) => [position, ...prev]);
          });
          showTradeExecuted({
            direction: position.type,
            asset: displayAsset,
            entryPrice: position.entryPrice,
            confidence: 90,
            stopLoss: position.stopLoss,
            takeProfit: position.takeProfit,
            reasoning: event.data.reasoning ?? "Position opened",
          });
          break;
        }
        case "position_closed": {
          if (!event.data) break;
          const trade: Trade = {
            id: `trade-${event.data.trade_number ?? Date.now()}`,
            tradeNumber: event.data.trade_number,
            type: event.data.action?.toLowerCase() === "short" ? "short" : "long",
            entryPrice: event.data.entry_price ?? 0,
            exitPrice: event.data.exit_price ?? 0,
            size: event.data.size ?? 0,
            pnl: event.data.pnl ?? 0,
            pnlPercent: event.data.pnl_pct ?? 0,
            entryTime: new Date(event.data.entry_time ?? Date.now()),
            exitTime: new Date(event.data.exit_time ?? Date.now()),
            reasoning: event.data.reasoning ?? "",
            confidence: 85,
            stopLoss: event.data.stop_loss ?? 0,
            takeProfit: event.data.take_profit ?? 0,
          };
          scheduleUpdate(() => {
            setTradesState((prev) => [trade, ...prev].slice(0, 100));
            setPositionsState((prev) =>
              prev.filter((pos) => pos.entryPrice !== trade.entryPrice)
            );
          });
          break;
        }
        case "countdown_update": {
          const secondsRemaining = event.data?.seconds_remaining ?? null;
          if (secondsRemaining !== null) {
            // Convert seconds to minutes for display (next candle)
            const minutes = Math.ceil(secondsRemaining / 60);
            setNextDecisionState(minutes);
          } else {
            setNextDecisionState(null);
          }
          
          // Get next AI intervention time
          const aiInterventionMinutes = event.data?.next_ai_intervention_minutes ?? null;
          if (aiInterventionMinutes !== null) {
            setNextAIDecisionState(aiInterventionMinutes);
          } else {
            setNextAIDecisionState(null);
          }
          break;
        }
        case "session_paused":
          setIsPausedState(true);
          break;
        case "session_resumed":
          setIsPausedState(false);
          break;
        case "session_completed":
          setIsPausedState(false);
          setIsStopped(true);
          setIsStopping(false);
          setRunningTimeState("Completed");
          // Show stopped message in dynamic island
          narrate("Forward test stopped. Results saved.", "result");
          // Disconnect websocket
          if (sessionId) {
            websocketManager.disconnect("forward", sessionId);
          }
          setIsConnectedState(false);
          // Navigate to result if available
          if (event.data?.result_id) {
            setTimeout(() => {
              router.push(`/dashboard/results/${event.data.result_id}`);
            }, 3000); // Increased to 3s to show stopped state
          }
          break;
        case "error":
          setForwardError(event.data?.message ?? "Session error");
          break;
      }
    },
    [displayAsset, forwardConfig?.capital, formatRunningTime, sessionId, scheduleUpdate]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
      flushUpdates();
      // Disconnect websocket on unmount if session is stopped
      if (isStopped && sessionId) {
        websocketManager.disconnect("forward", sessionId);
      }
    };
  }, [flushUpdates, isStopped, sessionId]);

  const { isConnected: wsConnected, error: wsError, reconnect } = useForwardWebSocket(sessionId, handleForwardEvent);

  useEffect(() => {
    setIsConnectedState(wsConnected);
    console.log("WebSocket connection status:", wsConnected, "Session ID:", sessionId);
    
    // When reconnecting, show loading state
    if (!wsConnected && hasReceivedInitialData) {
      setIsLoadingHistoricalData(true);
    }
  }, [wsConnected, sessionId, hasReceivedInitialData]);

  // Removed verbose logging - chart updates are working correctly
  
  // Detect when initial data has loaded
  useEffect(() => {
    // Wait for WebSocket connection AND candles to arrive before hiding loading
    // Don't hide just because sessionStats loaded from API - need WebSocket data!
    const hasData = isConnectedState && candlesState.length > 0;
    
    if (hasData && isLoadingHistoricalData) {
      setIsLoadingHistoricalData(false);
      setHasReceivedInitialData(true);
    }
  }, [candlesState.length, isConnectedState, isLoadingHistoricalData]);
  
  // Add a timeout fallback - if we're connected but no data after 10 seconds, stop loading
  useEffect(() => {
    if (!isLoadingHistoricalData || !isConnectedState) return;
    
    const timeout = setTimeout(() => {
      if (isLoadingHistoricalData && isConnectedState) {
        console.log("Data load timeout - showing interface anyway");
        setIsLoadingHistoricalData(false);
        setHasReceivedInitialData(true);
      }
    }, 10000); // 10 second timeout
    
    return () => clearTimeout(timeout);
  }, [isLoadingHistoricalData, isConnectedState]);

  useEffect(() => {
    if (wsError) {
      setForwardError(wsError);
    }
  }, [wsError]);

  // Dynamic Island controls - moved before handleStop to avoid hoisting issues
  const {
    showAnalyzing,
    showIdle,
    narrate,
    showTradeExecuted,
    showAlphaDetected,
    showConnectionStatus,
    celebrate,
    hide,
  } = useDynamicIslandStore();

  const handleStop = useCallback(async () => {
    if (!sessionId || isStopping || isStopped) return;
    setStopError(null);
    setIsStopping(true);
    
    // Show stopping message in dynamic island immediately
    narrate("Stopping forward test and closing positions...", "action");
    
    try {
      const response = await post(`/api/arena/forward/${sessionId}/stop`, {
        close_position: true,
      });
      const resultId = (response as { result_id?: string })?.result_id;
      
      // Update UI to show stopped state
      setIsStopped(true);
      setRunningTimeState("Stopped");
      
      // Disconnect websocket after stopping
      if (sessionId) {
        websocketManager.disconnect("forward", sessionId);
      }
      
      // Show success message
      narrate("Forward test stopped. Saving results...", "result");
      
      // Navigate after a short delay to show stopped state
      if (resultId) {
        setTimeout(() => {
          router.push(`/dashboard/results/${resultId}`);
        }, 2000);
      } else {
        setTimeout(() => {
          router.push("/dashboard/results");
        }, 2000);
      }
    } catch (err) {
      setIsStopping(false);
      setStopError(err instanceof Error ? err.message : "Failed to stop session");
      narrate("Failed to stop session. Please try again.", "result");
    }
  }, [post, router, sessionId, isStopping, isStopped, narrate]);
  
  // Find the selected agent
  const agent = useMemo(() => {
    if (!agents || agents.length === 0) {
      return null;
    }
    if (forwardConfig?.agentId) {
      return agents.find(a => a.id === forwardConfig.agentId) || agents[0] || null;
    }
    return agents[0] || null;
  }, [forwardConfig?.agentId, agents]);
  
  // Get config values with fallbacks
  const initialCapital = forwardConfig?.capital ?? 10000;
  const [isCompactLayout, setIsCompactLayout] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    thoughts: true,
    positions: true,
    trades: true,
  });
  
  // Calculate equity and pnl
  const calculatedEquity = sessionStats?.current_equity ?? initialCapital;
  const calculatedPnl = sessionStats?.current_pnl_pct ?? 0;
  const totalTrades = sessionStats?.trades_count ?? activeTrades.length;
  const winRate = sessionStats?.win_rate ?? 0;

  useEffect(() => {
    setIsCompactLayout(window.innerWidth < 768);
    const handleResize = () => {
      setIsCompactLayout(window.innerWidth < 768);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    setExpandedSections((prev) => {
      const next = isCompactLayout
        ? { thoughts: false, positions: false, trades: false }
        : { thoughts: true, positions: true, trades: true };
      if (prev.thoughts === next.thoughts && prev.positions === next.positions && prev.trades === next.trades) {
        return prev;
      }
      return next;
    });
  }, [isCompactLayout]);

  // ============================================
  // DYNAMIC ISLAND TRIGGERS
  // ============================================

  // Track for effects
  const prevPnlRef = useRef(calculatedPnl);
  const prevConnectionRef = useRef(isConnectedState);
  const lastNarratorTimeRef = useRef(0);

  // Show connection status changes
  useEffect(() => {
    if (isConnectedState !== prevConnectionRef.current) {
      showConnectionStatus({
        status: isConnectedState ? "connected" : "disconnected",
      });
      prevConnectionRef.current = isConnectedState;
    }
  }, [isConnectedState, showConnectionStatus]);

  // Show analyzing when running, idle when paused
  useEffect(() => {
    if (isPausedState) {
      narrate("Session paused - positions held", "info");
    } else if (!isPausedState && isConnectedState) {
      // Check if we're currently showing a trade or alpha (priority states)
      const islandState = useDynamicIslandStore.getState();
      const isPriorityMode = islandState.mode === "trade" || islandState.mode === "alpha" || islandState.mode === "celebration";
      
      // Only show analyzing if not in a priority state
      if (!isPriorityMode) {
      showAnalyzing({
        message: "Monitoring real-time market conditions...",
        phase: "analyzing",
        currentAsset: displayAsset,
        sessionId: sessionId,
        sessionType: "forward",
      });
      }
    }
  }, [isPausedState, isConnectedState, narrate, showAnalyzing]);

  // Initial mount - show forward test start
  useEffect(() => {
    narrate("Connecting to live market feed...", "info");
    return () => {
      hide();
    };
  }, [narrate, hide]);

  // Periodic narrator messages removed - use real AI thinking events instead

  // Track PnL for potential future use (celebration removed mid-test)
  useEffect(() => {
    // Just track the previous PnL, no celebration during live session
    prevPnlRef.current = calculatedPnl;
  }, [calculatedPnl]);

  // Track last trade count to detect new trades
  const lastTradeCountRef = useRef(0);
  const hasShownAlphaRef = useRef(false);
  
  // Alpha detection removed - will be triggered by real AI decision events with high confidence
  
  // Show trade executed when new trades appear
  useEffect(() => {
    if (activeTrades.length === 0) return;
    
    // Check if we have a new trade
    if (activeTrades.length > lastTradeCountRef.current) {
      const latestTrade = activeTrades[0];
      if (latestTrade) {
        const isLong = latestTrade.type === "long";
        
        // Use actual values from trade if available, otherwise calculate fallbacks
        const confidence = latestTrade.confidence ?? (Math.floor(Math.random() * 15) + 80);
        const stopLoss = latestTrade.stopLoss ?? (isLong 
          ? latestTrade.entryPrice * 0.97 
          : latestTrade.entryPrice * 1.03);
        const takeProfit = latestTrade.takeProfit ?? (isLong 
          ? latestTrade.entryPrice * 1.05 
          : latestTrade.entryPrice * 0.95);
        
        showTradeExecuted({
          direction: latestTrade.type as "long" | "short",
          asset: displayAsset,
          entryPrice: latestTrade.entryPrice,
          confidence,
          stopLoss: Math.round(stopLoss),
          takeProfit: Math.round(takeProfit),
          reasoning: latestTrade.reasoning, // Use actual reasoning from trade
        });
      }
      lastTradeCountRef.current = activeTrades.length;
    }
  }, [activeTrades, showTradeExecuted]);

  // Track last thought count to show AI thoughts in Dynamic Island
  const lastThoughtCountRef = useRef(0);
  
  // Show AI thoughts in Dynamic Island when new thoughts are added
  useEffect(() => {
    if (activeThoughts.length === 0 || isPausedState) return;
    
    // Check if we have a new thought
    if (activeThoughts.length > lastThoughtCountRef.current) {
      const latestThought = activeThoughts[0];
      if (latestThought && latestThought.type !== "execution") {
        // Only show non-execution thoughts (execution ones trigger trades)
        // Use narrator to show the thought briefly
        narrate(latestThought.content, "info");
      }
      lastThoughtCountRef.current = activeThoughts.length;
    }
  }, [activeThoughts, isPausedState, narrate]);

  const toggleSection = (section: keyof typeof expandedSections) => {
    if (!isCompactLayout) return;
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const showAllThoughts = !isCompactLayout || expandedSections.thoughts;
  const showAllPositions = !isCompactLayout || expandedSections.positions;
  const showAllTrades = !isCompactLayout || expandedSections.trades;

  const visibleThoughts = showAllThoughts ? activeThoughts : activeThoughts.slice(0, 1);
  const visiblePositions = showAllPositions ? activePositions : activePositions.slice(0, 1);
  const visibleTrades = showAllTrades ? activeTrades : activeTrades.slice(0, 1);

  const hiddenThoughts = Math.max(activeThoughts.length - visibleThoughts.length, 0);
  const hiddenPositions = Math.max(activePositions.length - visiblePositions.length, 0);
  const hiddenTrades = Math.max(activeTrades.length - visibleTrades.length, 0);

  const renderThought = (thought: AIThoughtType) => (
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
          ? "border-[hsl(var(--accent-green)/0.3)] bg-[hsl(var(--accent-green)/0.05)]"
          : "border-border/50 bg-muted/10"
      )}
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          {thought.action && (
            <Badge
              className={cn(
                "text-[10px] h-5",
                thought.action === "long" && "bg-[hsl(var(--accent-green))] text-black",
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
          {Math.round((Date.now() - (typeof thought.timestamp === 'number' ? thought.timestamp : thought.timestamp.getTime())) / 60000)}m ago
        </span>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{thought.content}</p>
    </motion.div>
  );

  // Show loading skeleton while reconnecting or loading initial data
  if (isLoadingHistoricalData && !forwardError) {
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
              {hasReceivedInitialData ? "Reconnecting to your session" : "Connecting to your session"}
            </h3>
            <p className="text-sm text-muted-foreground max-w-md">
              {!isConnectedState 
                ? "Establishing WebSocket connection..." 
                : hasReceivedInitialData 
                  ? "Loading latest data..." 
                  : "Loading session data..."}
            </p>
            {candlesState.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Received {candlesState.length} candles...
              </p>
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
  
  // Show error state if there's a critical error
  if (forwardError && candlesState.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-120px)] gap-4">
        <div className="flex flex-col items-center gap-3 max-w-md text-center">
          <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center">
            <WifiOff className="h-8 w-8 text-destructive" />
          </div>
          <h3 className="text-lg font-semibold">Connection Error</h3>
          <p className="text-sm text-muted-foreground">{forwardError}</p>
          <div className="flex gap-2 mt-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => {
                setForwardError(null);
                setIsLoadingHistoricalData(true);
                reconnect();
              }}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry Connection
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => router.push("/dashboard/arena/forward")}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Back to Arena
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-120px)] gap-2 sm:gap-3 pb-4">
      {/* Header - Mobile responsive */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        {/* Left: Back + Agent + Stats */}
        <div className="flex items-center gap-2 flex-wrap">
          <Link
            href="/dashboard/arena/forward"
            className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-card/50 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </Link>
          <span className="font-mono text-xs sm:text-sm font-medium">{agent?.name || "Loading..."}</span>
          <span className="text-[10px] sm:text-xs text-muted-foreground hidden xs:inline">{displayAsset}</span>
          <Separator orientation="vertical" className="h-3 hidden sm:block" />
          <div className="flex items-center gap-2 text-[10px] sm:text-xs">
            <span className="font-mono font-bold">${(calculatedEquity/1000).toFixed(1)}k</span>
            <span className={cn(
              "font-mono font-bold",
              calculatedPnl >= 0 ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
            )}>
              {calculatedPnl >= 0 ? "+" : ""}{calculatedPnl}%
            </span>
            <span className="text-muted-foreground hidden sm:inline">{activeTrades.length}T {winRate}%W</span>
          </div>
          <Badge
            variant="outline"
            className={cn(
              "text-[10px] h-5",
              isConnectedState
                ? "border-[hsl(var(--accent-green)/0.3)] text-[hsl(var(--accent-green))]"
                : "border-[hsl(var(--accent-red)/0.3)] text-[hsl(var(--accent-red))]"
            )}
          >
            {isConnectedState ? <Wifi className="h-3 w-3 mr-1" /> : <WifiOff className="h-3 w-3 mr-1" />}
            {isConnectedState ? "LIVE" : "OFF"}
          </Badge>
          {isPausedState && (
            <Badge variant="secondary" className="text-[10px] h-5">PAUSED</Badge>
          )}
          {isStopping && (
            <Badge variant="secondary" className="text-[10px] h-5">STOPPING...</Badge>
          )}
          {isStopped && (
            <Badge variant="secondary" className="text-[10px] h-5">STOPPED</Badge>
          )}
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button 
                variant="destructive" 
                size="sm" 
                className="h-7 px-2 gap-1"
                disabled={isStopping || isStopped}
              >
                <Square className="h-3 w-3" />
                <span className="hidden xs:inline">{isStopping ? "Stopping..." : isStopped ? "Stopped" : "Stop"}</span>
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Stop Forward Test?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will stop the live trading session and close any open positions.
                  Your results will be saved and a certificate can be generated if profitable.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleStop} className="bg-destructive">
                  Stop Session
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Running Time / Status */}
      <div className="flex items-center gap-2 text-[10px] sm:text-xs text-muted-foreground">
        <Clock className="h-3 w-3" />
        <span>
          {isStopped ? "Stopped" : isStopping ? "Stopping..." : `Running for ${activeRunningTime}`}
        </span>
        {nextAIDecisionState !== null && (
          <>
            <Separator orientation="vertical" className="h-3" />
            <span className="font-medium text-foreground">
              Next AI decision in {nextAIDecisionState}m
            </span>
          </>
        )}
      </div>

      {/* Main Content - Fills remaining space */}
      <div className="flex-1 flex flex-col gap-2 sm:gap-3 xl:grid xl:grid-cols-[1fr_240px] xl:gap-3 min-h-0 xl:overflow-hidden">
        {/* Left Column: Chart + AI Thoughts */}
        <div className="flex flex-col gap-2 sm:gap-3 xl:min-h-0 xl:overflow-hidden">
          {/* Chart */}
          <Card className="border-border/50 bg-card/30 shrink-0">
            <CardContent className="p-1.5 sm:p-2">
              {activeCandles.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[300px] text-center">
                  <Activity className="h-8 w-8 text-muted-foreground mb-2 animate-pulse" />
                  <p className="text-sm text-muted-foreground mb-1">
                    Waiting for first candle...
                  </p>
                  <p className="text-xs text-muted-foreground/70">
                    {activeNextAIDecision !== null
                      ? `Next AI decision in ${activeNextAIDecision} minutes`
                      : "Session initializing"}
                  </p>
                </div>
              ) : (
                <CandlestickChart
                  data={activeCandles}
                  height={300}
                  showVolume
                />
              )}
            </CardContent>
          </Card>

          {/* AI Thoughts - Takes remaining space, limited height on mobile */}
          <Card className="border-border/50 bg-card/30 flex-1 xl:min-h-0 min-h-[200px] xl:max-h-none flex flex-col xl:overflow-hidden">
            <CardHeader className="py-2 px-3 shrink-0">
              <CardTitle className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm">
                  <Robot size={16} weight="duotone" className="text-[hsl(var(--brand-flame))]" />
                  AI Thoughts
                </div>
                <div className="flex items-center gap-1.5">
                {activeThoughts.length > 0 && (
                  <span className="text-xs text-muted-foreground">{activeThoughts.length}</span>
                )}
                  {isCompactLayout && activeThoughts.length > 1 && (
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
              {activeThoughts.length === 0 ? (
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

        {/* Right Column: Open Positions (compact) + Trade Log */}
        <div className="flex flex-col gap-3 xl:min-h-0 xl:max-h-none">
          {/* Open Positions - Compact with border */}
          <div className="shrink-0 pb-3 border-b border-border/50 sm:max-h-[280px] sm:overflow-y-auto">
            <div className={cn(
              "mb-1.5 flex items-center justify-between px-1 pb-1.5",
              !isCompactLayout && "sticky top-0 bg-background/95 backdrop-blur-sm z-10"
            )}>
              <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                Open Positions
              </span>
              <span className="text-[10px] font-mono text-muted-foreground">{activePositions.length}</span>
              </div>
              {isCompactLayout && activePositions.length > 1 && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 px-2 text-[10px]"
                  onClick={() => toggleSection("positions")}
                >
                  {showAllPositions ? "Collapse" : "Expand"}
                </Button>
              )}
            </div>
            {activePositions.length > 0 ? (
              <div className="space-y-1.5">
                {visiblePositions.map((position, idx) => {
                  const topContent = (
                    <div className={cn(
                      "flex items-center justify-between rounded-t px-2 py-1.5",
                      position.type === "long"
                        ? "bg-[hsl(var(--accent-green)/0.15)]"
                        : "bg-[hsl(var(--accent-red)/0.15)]"
                    )}>
                      <div className="flex items-center gap-1.5">
                        <Badge className={cn(
                          "text-[8px] h-4 px-1",
                          position.type === "long" 
                            ? "bg-[hsl(var(--accent-green))] text-black" 
                            : "bg-[hsl(var(--accent-red))] text-white"
                        )}>
                          {position.type === "long" ? "L" : "S"}
                        </Badge>
                        <span className="font-mono text-[10px] text-foreground">
                          ${(position.entryPrice / 1000).toFixed(1)}k
                        </span>
                      </div>
                      <span className={cn(
                        "font-mono text-xs font-bold",
                        position.unrealizedPnL >= 0
                          ? "text-[hsl(var(--accent-green))]"
                          : "text-[hsl(var(--accent-red))]"
                      )}>
                        {position.unrealizedPnL >= 0 ? "+" : ""}${position.unrealizedPnL.toFixed(2)}
                      </span>
                    </div>
                  );

                  const middleContent = (
                    <div className="px-2 py-1 text-center">
                      <p className="text-[9px] text-muted-foreground">Size</p>
                      <p className="font-mono text-[10px] font-medium">{position.size} BTC</p>
                    </div>
                  );

                  const bottomContent = (
                    <div className={cn(
                      "px-2 pb-2 pt-1 space-y-1.5 border-t",
                      position.type === "long"
                        ? "bg-[hsl(var(--accent-green)/0.05)] border-[hsl(var(--accent-green)/0.2)]"
                        : "bg-[hsl(var(--accent-red)/0.05)] border-[hsl(var(--accent-red)/0.2)]"
                    )}>
                      <div className="grid grid-cols-2 gap-1.5">
                        <div className="rounded border border-border/50 bg-muted/20 p-1.5">
                          <p className="text-[9px] text-muted-foreground">Stop Loss</p>
                          <p className="font-mono text-[10px] font-medium text-[hsl(var(--accent-red))]">
                            ${(position.stopLoss / 1000).toFixed(1)}k
                          </p>
                        </div>
                        <div className="rounded border border-border/50 bg-muted/20 p-1.5">
                          <p className="text-[9px] text-muted-foreground">Take Profit</p>
                          <p className="font-mono text-[10px] font-medium text-[hsl(var(--accent-green))]">
                            ${(position.takeProfit / 1000).toFixed(1)}k
                          </p>
                        </div>
                      </div>
                    </div>
                  );

                  return (
                    <ShiftCard
                      key={`${position.entryPrice}-${idx}`}
                      className={cn(
                        "border",
                        position.type === "long"
                          ? "border-[hsl(var(--accent-green)/0.3)]"
                          : "border-[hsl(var(--accent-red)/0.3)]"
                      )}
                      topContent={topContent}
                      middleContent={middleContent}
                      bottomContent={bottomContent}
                    />
                  );
                })}
              </div>
            ) : (
              <Card className="border-border/50 bg-card/30">
                <CardContent className="p-3 text-center">
                  <Activity className="h-4 w-4 mx-auto mb-1 opacity-40 text-muted-foreground" />
                  <p className="text-[10px] text-muted-foreground">No open positions</p>
                </CardContent>
              </Card>
            )}
            {isCompactLayout && !showAllPositions && hiddenPositions > 0 && (
              <p className="text-[10px] text-muted-foreground text-center mt-1">
                +{hiddenPositions} more positions
              </p>
            )}
          </div>

          {/* Trade Log - Takes remaining space */}
          <div className="flex-1 flex flex-col border border-border/50 rounded-lg bg-card/30 overflow-hidden min-h-0 xl:min-h-[300px] min-h-[200px]">
            <div className={cn(
              "px-2 py-1.5 border-b border-border/50 bg-muted/30 flex items-center justify-between shrink-0",
              !isCompactLayout && "sticky top-0 z-10"
            )}>
              <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                Trades
              </span>
            <span className="text-[10px] font-mono text-muted-foreground">{activeTrades.length}</span>
              </div>
              {isCompactLayout && activeTrades.length > 1 && (
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
              <div className="p-1.5 space-y-1.5 pb-3">
                {activeTrades.length === 0 ? (
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
                          ? "bg-[hsl(var(--accent-green)/0.15)]" 
                          : "bg-[hsl(var(--accent-red)/0.15)]"
                      )}>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-xs font-bold text-foreground">
                            #{index + 1}
                          </span>
                          <Badge className={cn(
                            "text-[8px] h-4 px-1",
                            trade.type === "long" ? "bg-[hsl(var(--accent-green))] text-black" : "bg-[hsl(var(--accent-red))] text-white"
                          )}>
                            {trade.type === "long" ? "L" : "S"}
                          </Badge>
                        </div>
                        <span className={cn(
                          "font-mono text-sm font-bold",
                          trade.pnl >= 0 ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
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
                          ? "bg-[hsl(var(--accent-green)/0.05)] border-[hsl(var(--accent-green)/0.2)]" 
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
                            ? "bg-[hsl(var(--accent-green)/0.15)]" 
                            : "bg-[hsl(var(--accent-red)/0.15)]"
                        )}>
                          <p className="text-[9px] text-muted-foreground">P/L</p>
                          <p className={cn(
                            "font-mono text-xs font-bold",
                            trade.pnl >= 0 ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
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
                            ? "border-[hsl(var(--accent-green)/0.3)]" 
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
              <ScrollArea className="flex-1 min-h-0">
                <div className="p-1.5 space-y-1.5 pb-3">
              {activeTrades.length === 0 ? (
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
                        ? "bg-[hsl(var(--accent-green)/0.15)]" 
                        : "bg-[hsl(var(--accent-red)/0.15)]"
                    )}>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-bold text-foreground">
                          #{index + 1}
                        </span>
                        <Badge className={cn(
                          "text-[8px] h-4 px-1",
                          trade.type === "long" ? "bg-[hsl(var(--accent-green))] text-black" : "bg-[hsl(var(--accent-red))] text-white"
                        )}>
                          {trade.type === "long" ? "L" : "S"}
                        </Badge>
                      </div>
                      <span className={cn(
                        "font-mono text-sm font-bold",
                        trade.pnl >= 0 ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
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
                        ? "bg-[hsl(var(--accent-green)/0.05)] border-[hsl(var(--accent-green)/0.2)]" 
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
                          ? "bg-[hsl(var(--accent-green)/0.15)]" 
                          : "bg-[hsl(var(--accent-red)/0.15)]"
                      )}>
                        <p className="text-[9px] text-muted-foreground">P/L</p>
                        <p className={cn(
                          "font-mono text-xs font-bold",
                          trade.pnl >= 0 ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
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
                          ? "border-[hsl(var(--accent-green)/0.3)]" 
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
    </div>
  );
}

