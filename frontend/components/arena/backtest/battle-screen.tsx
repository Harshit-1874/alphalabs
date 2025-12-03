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
} from "lucide-react";
import { Robot } from "@phosphor-icons/react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
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
  DUMMY_AI_THOUGHTS,
  DUMMY_TRADES,
  DUMMY_AGENTS,
} from "@/lib/dummy-data";
import { useAgentsStore, useArenaStore, useDynamicIslandStore } from "@/lib/stores";
import {
  NARRATOR_MESSAGES,
  getRandomNarratorMessage,
  createMockTradeData,
  createMockAlphaData,
  createMockCelebrationData,
} from "@/lib/dummy-island-data";
import type { CandleData, AIThought, Trade, PlaybackSpeed } from "@/types";

interface BattleScreenProps {
  sessionId: string;
}

export function BattleScreen({ sessionId }: BattleScreenProps) {
  const router = useRouter();
  
  // Get config and agents from stores
  const { backtestConfig } = useArenaStore();
  const { agents } = useAgentsStore();
  
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
  
  // Find the selected agent
  const agent = useMemo(() => {
    if (backtestConfig?.agentId) {
      return agents.find(a => a.id === backtestConfig.agentId) || DUMMY_AGENTS[0];
    }
    return DUMMY_AGENTS[0];
  }, [backtestConfig?.agentId, agents]);
  
  // Get config values with fallbacks
  const initialCapital = backtestConfig?.capital ?? 10000;
  const asset = backtestConfig?.asset ?? "btc-usdt";
  const timeframe = backtestConfig?.timeframe ?? "1h";
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<PlaybackSpeed>(backtestConfig?.speed ?? "normal");
  const [currentCandle, setCurrentCandle] = useState(0);
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [visibleCandles, setVisibleCandles] = useState<CandleData[]>([]);
  const [thoughts, setThoughts] = useState<AIThought[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [equity, setEquity] = useState(initialCapital);
  const [pnl, setPnl] = useState(0);
  const [isCompactLayout, setIsCompactLayout] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    thoughts: true,
    trades: true,
  });

  const totalCandles = 200;

  // Initialize candles
  useEffect(() => {
    const generated = generateDummyCandles(totalCandles);
    setCandles(generated);
    setVisibleCandles(generated.slice(0, 1));
  }, []);

  // Playback logic
  useEffect(() => {
    if (!isPlaying || currentCandle >= totalCandles - 1) return;

    const speedMs = {
      slow: 1000,
      normal: 500,
      fast: 200,
      instant: 0,
    }[speed];

    if (speed === "instant") {
      // Show all candles immediately
      setVisibleCandles(candles);
      setCurrentCandle(totalCandles - 1);
      setIsPlaying(false);
      return;
    }

    const interval = setInterval(() => {
      setCurrentCandle((prev) => {
        const next = prev + 1;
        if (next >= totalCandles - 1) {
          setIsPlaying(false);
        }
        return next;
      });
    }, speedMs);

    return () => clearInterval(interval);
  }, [isPlaying, speed, totalCandles, candles]);

  // Update visible candles
  useEffect(() => {
    setVisibleCandles(candles.slice(0, currentCandle + 1));

    // Simulate PnL changes
    const basePnl = Math.sin(currentCandle / 20) * 15 + (currentCandle / totalCandles) * 20;
    setPnl(Number(basePnl.toFixed(2)));
    setEquity(10000 * (1 + basePnl / 100));

    // Add AI thoughts at certain intervals
    if (currentCandle > 0 && currentCandle % 30 === 0) {
      const thought = DUMMY_AI_THOUGHTS[Math.floor(Math.random() * DUMMY_AI_THOUGHTS.length)];
      setThoughts((prev) => [{ ...thought, id: `thought-${currentCandle}`, candle: currentCandle }, ...prev].slice(0, 20));
    }

    // Add trades at certain intervals
    if (currentCandle > 0 && currentCandle % 50 === 0) {
      const trade = DUMMY_TRADES[Math.floor(Math.random() * DUMMY_TRADES.length)];
      setTrades((prev) => [{ ...trade, id: `trade-${currentCandle}` }, ...prev].slice(0, 10));
    }
  }, [currentCandle, candles, totalCandles]);

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

  const handleStop = useCallback(() => {
    setIsPlaying(false);
    // Navigate to results
    router.push(`/dashboard/results/demo-${sessionId}`);
  }, [router, sessionId]);

  const progress = (currentCandle / (totalCandles - 1)) * 100;

  const winRate = trades.length > 0
    ? Math.round((trades.filter((t) => t.pnl > 0).length / trades.length) * 100)
    : 0;

  // ============================================
  // DYNAMIC ISLAND TRIGGERS
  // ============================================

  // Track previous PnL for profit crossing detection
  const prevPnlRef = useRef(0);
  const hasShownAlphaRef = useRef(false);
  const lastNarratorCandleRef = useRef(0);

  // Show analyzing when playback starts
  useEffect(() => {
    if (isPlaying && currentCandle === 0) {
      narrate(NARRATOR_MESSAGES.backtestStart, "info");
    } else if (isPlaying) {
      // Check if we're currently showing a trade or alpha (priority states)
      const islandState = useDynamicIslandStore.getState();
      const isPriorityMode = islandState.mode === "trade" || islandState.mode === "alpha" || islandState.mode === "celebration";
      
      // Only show analyzing if not in a priority state
      if (!isPriorityMode) {
        // Show what AI is doing - phase based on progress
        const phase = currentCandle < totalCandles * 0.3 ? "scanning" : 
                     currentCandle < totalCandles * 0.7 ? "analyzing" : "deciding";
        showAnalyzing({
          message: NARRATOR_MESSAGES.analyzing,
          phase,
          currentAsset: asset.toUpperCase().replace("-", "/"),
        });
      }
    } else if (!isPlaying && currentCandle > 0 && progress < 100) {
      showIdle();
    }
  }, [isPlaying, currentCandle, progress, totalCandles, asset, narrate, showAnalyzing, showIdle]);

  // Narrator messages at intervals during playback
  useEffect(() => {
    if (!isPlaying || speed === "instant") return;
    
    // Show narrator every ~20 candles (but not too frequently)
    if (currentCandle > 0 && currentCandle % 20 === 0 && currentCandle !== lastNarratorCandleRef.current) {
      lastNarratorCandleRef.current = currentCandle;
      const message = getRandomNarratorMessage();
      narrate(message.text, message.type);
    }
  }, [currentCandle, isPlaying, speed, narrate]);

  // Show alpha detected occasionally (once per session, around 40% progress)
  useEffect(() => {
    if (!isPlaying || hasShownAlphaRef.current) return;
    
    const progressPercent = (currentCandle / totalCandles) * 100;
    if (progressPercent >= 35 && progressPercent <= 45) {
      hasShownAlphaRef.current = true;
      const alphaData = createMockAlphaData(Math.random() > 0.5 ? "long" : "short", "BTC/USDT");
      showAlphaDetected(alphaData);
    }
  }, [currentCandle, isPlaying, totalCandles, showAlphaDetected]);

  // Track last trade count to detect new trades
  const lastTradeCountRef = useRef(0);
  
  // Show trade executed when new trades are added
  useEffect(() => {
    if (trades.length === 0) return;
    
    // Check if we have a new trade
    if (trades.length > lastTradeCountRef.current) {
      const latestTrade = trades[0];
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
          asset: asset.toUpperCase().replace("-", "/"),
          entryPrice: latestTrade.entryPrice,
          confidence,
          stopLoss: Math.round(stopLoss),
          takeProfit: Math.round(takeProfit),
          reasoning: latestTrade.reasoning, // Use actual reasoning from trade
        });
      }
      lastTradeCountRef.current = trades.length;
    }
  }, [trades, asset, showTradeExecuted]);

  // Track last thought count to show AI thoughts in Dynamic Island
  const lastThoughtCountRef = useRef(0);
  
  // Show AI thoughts in Dynamic Island when new thoughts are added
  useEffect(() => {
    if (thoughts.length === 0 || !isPlaying) return;
    
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
  }, [thoughts, isPlaying, narrate]);

  // Celebrate when crossing into profit (REMOVED - only celebrate at end)
  useEffect(() => {
    // Just track the previous PnL, no celebration mid-test
    prevPnlRef.current = pnl;
  }, [pnl]);

  // Celebrate on completion if profitable
  useEffect(() => {
    if (progress >= 100 && pnl > 0) {
      narrate(NARRATOR_MESSAGES.backtestComplete, "result");
      setTimeout(() => {
        celebrate({
          pnl,
          trades: trades.length,
          winRate,
        });
      }, 2500);
    }
  }, [progress, pnl, trades.length, winRate, narrate, celebrate]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      hide();
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
          <span className="font-mono text-xs sm:text-sm font-medium">{agent.name}</span>
          <span className="text-[10px] sm:text-xs text-muted-foreground hidden xs:inline">BTC/USDT</span>
          <Separator orientation="vertical" className="h-3 hidden sm:block" />
          <div className="flex items-center gap-2 text-[10px] sm:text-xs">
            <span className="font-mono font-bold">${(equity/1000).toFixed(1)}k</span>
            <span className={cn(
              "font-mono font-bold",
              pnl >= 0 ? "text-[hsl(var(--accent-profit))]" : "text-[hsl(var(--accent-red))]"
            )}>
              {pnl >= 0 ? "+" : ""}{pnl}%
            </span>
            <span className="text-muted-foreground hidden sm:inline">{trades.length}T {winRate}%W</span>
          </div>
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          <div className="flex items-center rounded-md border border-border bg-card/50 p-0.5">
            {["slow", "normal", "fast", "instant"].map((s) => (
              <Button
                key={s}
                variant="ghost"
                size="sm"
                onClick={() => setSpeed(s as PlaybackSpeed)}
                className={cn("h-6 px-1.5 sm:px-2 text-[10px] sm:text-xs", speed === s && "bg-muted")}
              >
                {s === "instant" ? <SkipForward className="h-3 w-3" /> : s === "slow" ? "1x" : s === "normal" ? "2x" : "5x"}
              </Button>
            ))}
          </div>

          {progress < 100 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsPlaying(!isPlaying)}
              className="gap-1 h-7 px-2 text-xs"
            >
              {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
              <span className="hidden xs:inline">{isPlaying ? "Pause" : currentCandle === 0 ? "Start" : "Resume"}</span>
            </Button>
          )}

          {currentCandle > 0 && progress < 100 && (
            <Button variant="destructive" size="sm" onClick={handleStop} className="h-7 px-2">
              <Square className="h-3 w-3" />
            </Button>
          )}

          {progress >= 100 && (
            <Button 
              size="sm" 
              onClick={handleStop} 
              className="h-7 px-2 text-xs bg-[hsl(var(--accent-profit))] text-black hover:bg-[hsl(var(--accent-profit))]/90"
            >
              Results
            </Button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="flex items-center gap-2">
        <Progress value={progress} className="h-1 sm:h-1.5 flex-1" />
        <span className="text-[10px] sm:text-xs text-muted-foreground">{progress.toFixed(0)}%</span>
      </div>

      {/* Main Content - Fills remaining space */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_220px] gap-2 sm:gap-3 min-h-0">
        {/* Left Column: Chart + AI Thoughts */}
        <div className="flex flex-col gap-2 sm:gap-3 min-h-0">
          {/* Chart */}
          <Card className="border-border/50 bg-card/30 shrink-0">
            <CardContent className="p-1.5 sm:p-2">
              <CandlestickChart
                data={visibleCandles}
                height={300}
                showVolume
              />
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

