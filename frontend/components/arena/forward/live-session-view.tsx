"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronLeft,
  Play,
  Pause,
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
import {
  generateDummyCandles,
  DUMMY_TRADES,
  DUMMY_AGENTS,
  DUMMY_AI_THOUGHTS,
} from "@/lib/dummy-data";
import { useAgentsStore, useArenaStore, useDynamicIslandStore } from "@/lib/stores";
import {
  NARRATOR_MESSAGES,
  getRandomNarratorMessage,
  createMockTradeData,
  createMockCelebrationData,
  createMockAlphaData,
} from "@/lib/dummy-island-data";
import type { CandleData, Trade, Position, AIThought as AIThoughtType } from "@/types";

interface AIThought {
  id: string;
  content: string;
  type: "analysis" | "decision" | "execution";
  action?: "long" | "short" | "hold";
  timestamp: number;
}

interface LiveSessionViewProps {
  sessionId: string;
  positions?: Position[];
  thoughts?: AIThought[];
  trades?: Trade[];
  candles?: CandleData[];
  equity?: number;
  pnl?: number;
  isConnected?: boolean;
  isPaused?: boolean;
  runningTime?: string;
  nextDecision?: number;
  onPauseToggle?: () => void;
  onStop?: () => void;
}

export function LiveSessionView({ 
  sessionId,
  positions,
  thoughts,
  trades,
  candles,
  equity,
  pnl,
  isConnected = true,
  isPaused = false,
  runningTime,
  nextDecision,
  onPauseToggle,
  onStop,
}: LiveSessionViewProps) {
  // Get config and agents from stores
  const { forwardConfig } = useArenaStore();
  const { agents } = useAgentsStore();
  
  // Dynamic Island controls
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
  
  // Find the selected agent
  const agent = useMemo(() => {
    if (forwardConfig?.agentId) {
      return agents.find(a => a.id === forwardConfig.agentId) || DUMMY_AGENTS[0];
    }
    return DUMMY_AGENTS[0];
  }, [forwardConfig?.agentId, agents]);
  
  // Get config values with fallbacks
  const initialCapital = forwardConfig?.capital ?? 10000;
  
  // Internal state for demo/simulation
  const [internalCandles, setInternalCandles] = useState<CandleData[]>([]);
  const [internalTrades, setInternalTrades] = useState<Trade[]>(DUMMY_TRADES.slice(0, 2));
  const [internalThoughts, setInternalThoughts] = useState<AIThought[]>(
    DUMMY_AI_THOUGHTS.slice(0, 3).map((t: AIThoughtType, i: number) => ({
      id: `thought-${i}`,
      content: t.content,
      type: t.type,
      action: t.action === "close" ? undefined : t.action,
      timestamp: Date.now() - (3 - i) * 2 * 60 * 1000,
    }))
  );
  const [internalPositions, setInternalPositions] = useState<Position[]>([
    {
      type: "long",
      entryPrice: 43250,
      size: 0.5,
      leverage: 1,
      stopLoss: 42500,
      takeProfit: 44500,
      unrealizedPnL: 325,
      openedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    },
    {
      type: "short",
      entryPrice: 44100,
      size: 0.3,
      leverage: 1,
      stopLoss: 44800,
      takeProfit: 43200,
      unrealizedPnL: -85,
      openedAt: new Date(Date.now() - 1 * 60 * 60 * 1000),
    },
  ]);
  const [internalRunningTime, setInternalRunningTime] = useState("4h 23m");
  const [internalNextDecision, setInternalNextDecision] = useState(42);
  const [isCompactLayout, setIsCompactLayout] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    thoughts: true,
    positions: true,
    trades: true,
  });
  
  // Use props if provided, otherwise use internal state
  const activeCandles = candles || internalCandles;
  const activeTrades = trades || internalTrades;
  const activeThoughts = thoughts || internalThoughts;
  const activePositions = positions || internalPositions;
  const activeRunningTime = runningTime || internalRunningTime;
  const activeNextDecision = nextDecision || internalNextDecision;
  
  // Calculate equity and pnl
  const calculatedEquity = equity ?? (
    initialCapital + activePositions.reduce((sum, p) => sum + p.unrealizedPnL, 0)
  );
  const calculatedPnl = pnl ?? Number(
    ((activePositions.reduce((sum, p) => sum + p.unrealizedPnL, 0) / initialCapital) * 100).toFixed(2)
  );
  
  const winRate = activeTrades.length > 0
    ? Math.round((activeTrades.filter((t) => t.pnl > 0).length / activeTrades.length) * 100)
    : 0;

  // Initialize candles if not provided
  useEffect(() => {
    if (!candles) {
      setInternalCandles(generateDummyCandles(100));
    }
  }, [candles]);
  
  // Simulate live updates if not controlled by props
  useEffect(() => {
    if (candles || isPaused) return;

    const interval = setInterval(() => {
      // Add new candle
      setInternalCandles((prev) => {
        if (prev.length === 0) return prev;
        const lastCandle = prev[prev.length - 1];
        const newCandle: CandleData = {
          time: lastCandle.time + 60 * 60 * 1000,
          open: lastCandle.close,
          high: lastCandle.close * (1 + Math.random() * 0.01),
          low: lastCandle.close * (1 - Math.random() * 0.01),
          close: lastCandle.close * (1 + (Math.random() - 0.5) * 0.02),
          volume: Math.random() * 1000,
        };
        return [...prev.slice(-99), newCandle];
      });

      // Update position PnL
      setInternalPositions((prev) =>
        prev.map((p) => ({
          ...p,
          unrealizedPnL: p.unrealizedPnL + (Math.random() - 0.5) * 50,
        }))
      );
    }, 5000);

    return () => clearInterval(interval);
  }, [candles, isPaused]);
  
  // Countdown timer if not controlled
  useEffect(() => {
    if (nextDecision !== undefined || isPaused) return;
    
    const interval = setInterval(() => {
      setInternalNextDecision((prev) => {
        if (prev <= 1) return 60;
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [nextDecision, isPaused]);

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
        ? { thoughts: false, positions: false, trades: false }
        : { thoughts: true, positions: true, trades: true };
      return (
        prev.thoughts === next.thoughts &&
        prev.positions === next.positions &&
        prev.trades === next.trades
      )
        ? prev
        : next;
    });
  }, [isCompactLayout]);

  const handlePauseToggle = () => {
    if (onPauseToggle) {
      onPauseToggle();
    }
  };

  const handleStop = () => {
    if (onStop) {
      onStop();
    } else {
      // Default fallback
      window.location.href = `/dashboard/results/forward-${sessionId}`;
    }
  };

  // ============================================
  // DYNAMIC ISLAND TRIGGERS
  // ============================================

  // Track for effects
  const prevPnlRef = useRef(calculatedPnl);
  const prevConnectionRef = useRef(isConnected);
  const lastNarratorTimeRef = useRef(0);

  // Show connection status changes
  useEffect(() => {
    if (isConnected !== prevConnectionRef.current) {
      showConnectionStatus({
        status: isConnected ? "connected" : "disconnected",
      });
      prevConnectionRef.current = isConnected;
    }
  }, [isConnected, showConnectionStatus]);

  // Show analyzing when running, idle when paused
  useEffect(() => {
    if (isPaused) {
      narrate(NARRATOR_MESSAGES.forwardPaused, "info");
    } else if (!isPaused && isConnected) {
      // Check if we're currently showing a trade or alpha (priority states)
      const islandState = useDynamicIslandStore.getState();
      const isPriorityMode = islandState.mode === "trade" || islandState.mode === "alpha" || islandState.mode === "celebration";
      
      // Only show analyzing if not in a priority state
      if (!isPriorityMode) {
      showAnalyzing({
        message: NARRATOR_MESSAGES.forwardAnalyzing,
        phase: "analyzing",
        currentAsset: "BTC/USDT",
      });
      }
    }
  }, [isPaused, isConnected, narrate, showAnalyzing]);

  // Initial mount - show forward test start
  useEffect(() => {
    narrate(NARRATOR_MESSAGES.forwardStart, "info");
    return () => {
      hide();
    };
  }, [narrate, hide]);

  // Periodic narrator messages (every 30 seconds while running)
  useEffect(() => {
    if (isPaused || !isConnected) return;

    const interval = setInterval(() => {
      const now = Date.now();
      if (now - lastNarratorTimeRef.current > 25000) {
        lastNarratorTimeRef.current = now;
        const message = getRandomNarratorMessage();
        narrate(message.text, message.type);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [isPaused, isConnected, narrate]);

  // Track PnL for potential future use (celebration removed mid-test)
  useEffect(() => {
    // Just track the previous PnL, no celebration during live session
    prevPnlRef.current = calculatedPnl;
  }, [calculatedPnl]);

  // Track last trade count to detect new trades
  const lastTradeCountRef = useRef(0);
  const hasShownAlphaRef = useRef(false);
  
  // Show alpha detected occasionally (once per session, after some time)
  useEffect(() => {
    if (isPaused || !isConnected || hasShownAlphaRef.current) return;
    
    // Show alpha after 2 minutes if PnL is positive
    const timeout = setTimeout(() => {
      if (calculatedPnl > 0 && !hasShownAlphaRef.current) {
        hasShownAlphaRef.current = true;
        const direction = Math.random() > 0.5 ? "long" : "short";
        showAlphaDetected(createMockAlphaData(direction, "BTC/USDT"));
      }
    }, 120000); // 2 minutes
    
    return () => clearTimeout(timeout);
  }, [isPaused, isConnected, calculatedPnl, showAlphaDetected]);
  
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
          asset: "BTC/USDT",
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
    if (activeThoughts.length === 0 || isPaused) return;
    
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
  }, [activeThoughts, isPaused, narrate]);

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
          {Math.round((Date.now() - thought.timestamp) / 60000)}m ago
        </span>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{thought.content}</p>
    </motion.div>
  );

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
          <span className="font-mono text-xs sm:text-sm font-medium">{agent.name}</span>
          <span className="text-[10px] sm:text-xs text-muted-foreground hidden xs:inline">BTC/USDT</span>
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
              isConnected
                ? "border-[hsl(var(--accent-green)/0.3)] text-[hsl(var(--accent-green))]"
                : "border-[hsl(var(--accent-red)/0.3)] text-[hsl(var(--accent-red))]"
            )}
          >
            {isConnected ? <Wifi className="h-3 w-3 mr-1" /> : <WifiOff className="h-3 w-3 mr-1" />}
            {isConnected ? "LIVE" : "OFF"}
          </Badge>
          {isPaused && (
            <Badge variant="secondary" className="text-[10px] h-5">PAUSED</Badge>
          )}
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePauseToggle}
            className={cn(
              "gap-1 h-7 px-2 text-xs",
              isPaused && "border-[hsl(var(--accent-amber)/0.5)] text-[hsl(var(--accent-amber))]"
            )}
          >
            {isPaused ? <Play className="h-3 w-3" /> : <Pause className="h-3 w-3" />}
            <span className="hidden xs:inline">{isPaused ? "Resume" : "Pause"}</span>
          </Button>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button 
                variant={isPaused ? "destructive" : "outline"} 
                size="sm" 
                className={cn(
                  "h-7 px-2",
                  !isPaused && "border-destructive/50 text-destructive hover:bg-destructive/10"
                )}
              >
                <Square className="h-3 w-3" />
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
        <span>Running for {activeRunningTime}</span>
        <Separator orientation="vertical" className="h-3" />
        <span>Next decision in {activeNextDecision}m</span>
      </div>

      {/* Main Content - Fills remaining space */}
      <div className="flex-1 flex flex-col gap-2 sm:gap-3 xl:grid xl:grid-cols-[1fr_240px] xl:gap-3 min-h-0 xl:overflow-hidden">
        {/* Left Column: Chart + AI Thoughts */}
        <div className="flex flex-col gap-2 sm:gap-3 xl:min-h-0 xl:overflow-hidden">
          {/* Chart */}
          <Card className="border-border/50 bg-card/30 shrink-0">
            <CardContent className="p-1.5 sm:p-2">
              <CandlestickChart
                data={activeCandles}
                height={300}
                showVolume
              />
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

