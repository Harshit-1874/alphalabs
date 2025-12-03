"use client";

import { useState, useEffect } from "react";
import { Plus, Zap, Bot, History, Play, X } from "lucide-react";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "@/components/ui/button";
import {
  AnimatedSelect,
  AnimatedSelectContent,
  AnimatedSelectItem,
  AnimatedSelectTrigger,
  AnimatedSelectValue,
} from "@/components/ui/animated-select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAgentsStore, useDynamicIslandStore } from "@/lib/stores";
import {
  ExpandableScreen,
  ExpandableScreenTrigger,
  ExpandableScreenContent,
  useExpandableScreen,
} from "@/components/ui/expandable-screen";
import type { Agent } from "@/types/agent";

// Random motivational quotes for the subtitle
const motivationalQuotes = [
  "Ready to train some fighters?",
  "The market awaits your AI.",
  "Time to prove your strategy.",
  "Let's build something legendary.",
  "Your next alpha is waiting.",
];

export function DashboardHeader() {
  const { user } = useUser();
  const router = useRouter();
  const { agents } = useAgentsStore();
  
  // Dynamic Island
  const { showIdle, showLiveSession, hide } = useDynamicIslandStore();
  
  // Show island state on dashboard mount
  useEffect(() => {
    // Import dynamically to avoid SSR issues
    const checkLiveSessions = async () => {
      const { getPrimaryLiveSession } = await import("@/lib/dummy-island-data");
      const liveSession = getPrimaryLiveSession();
      
      if (liveSession) {
        // Show live session status with ALL expanded view data
        showLiveSession({
          agentName: liveSession.agentName,
          pnl: liveSession.pnl,
          duration: liveSession.duration,
          status: liveSession.status,
          // Include expanded view fields
          openPositions: liveSession.openPositions,
          totalTrades: liveSession.totalTrades,
          winRate: liveSession.winRate,
          equity: liveSession.equity,
          nextDecisionIn: liveSession.nextDecisionIn,
        });
      } else {
        // No active sessions, show idle state
        showIdle();
      }
    };
    
    // Small delay to let the page render first
    const timer = setTimeout(checkLiveSessions, 500);
    
    return () => {
      clearTimeout(timer);
      hide();
    };
  }, [showIdle, showLiveSession, hide]);
  
  // Quick test state
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [testType, setTestType] = useState<"backtest" | "forward">("backtest");
  
  const agent = agents.find((a) => a.id === selectedAgent);
  const canForwardTest: boolean = !!(agent && (agent.stats.profitableTests ?? 0) > 0);
  
  // Get time-based greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const firstName = user?.firstName || "Trader";
  
  // Get a random quote (in real app, could be deterministic per session)
  const quote = motivationalQuotes[Math.floor(Math.random() * motivationalQuotes.length)];

  const handleStartTest = (collapse: () => void) => {
    if (!selectedAgent) return;
    
    const path = testType === "backtest" 
      ? `/dashboard/arena/backtest?agent=${selectedAgent}`
      : `/dashboard/arena/forward?agent=${selectedAgent}`;
    
    collapse();
    setTimeout(() => router.push(path), 300);
  };

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      {/* Left: Greeting */}
      <div className="space-y-1">
        <h1 className="font-mono text-2xl font-bold tracking-tight text-foreground md:text-3xl">
          {getGreeting()}, {firstName}
        </h1>
        <p className="text-sm text-muted-foreground md:text-base">
          {quote}
        </p>
      </div>

      {/* Right: Quick Actions */}
      <div className="flex items-center gap-3">
        {/* Quick Test - Expandable */}
        <ExpandableScreen
          layoutId="quick-test-morph"
          triggerRadius="6px"
          contentRadius="16px"
          animationDuration={0.4}
        >
          <ExpandableScreenTrigger>
            <Button 
              variant="outline" 
              size="sm" 
              className="gap-2"
            >
              <Zap className="h-4 w-4" />
              <span className="hidden sm:inline">Quick Test</span>
            </Button>
          </ExpandableScreenTrigger>
          
          <ExpandableScreenContent 
            className="bg-background border border-border"
            showCloseButton={false}
          >
            <QuickTestContent 
              agents={agents}
              selectedAgent={selectedAgent}
              setSelectedAgent={setSelectedAgent}
              testType={testType}
              setTestType={setTestType}
              canForwardTest={canForwardTest}
              onStartTest={handleStartTest}
            />
          </ExpandableScreenContent>
        </ExpandableScreen>

        {/* New Agent - Smooth Navigation */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: "spring", stiffness: 400, damping: 17 }}
        >
          <Button 
            size="sm" 
            className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
            onClick={() => router.push("/dashboard/agents/new")}
          >
            <Plus className="h-4 w-4" />
            <span>New Agent</span>
          </Button>
        </motion.div>
      </div>
    </div>
  );
}

// Quick Test Content Component
function QuickTestContent({
  agents,
  selectedAgent,
  setSelectedAgent,
  testType,
  setTestType,
  canForwardTest,
  onStartTest,
}: {
  agents: Agent[];
  selectedAgent: string;
  setSelectedAgent: (id: string) => void;
  testType: "backtest" | "forward";
  setTestType: (type: "backtest" | "forward") => void;
  canForwardTest: boolean;
  onStartTest: (collapse: () => void) => void;
}) {
  const { collapse } = useExpandableScreen();

  return (
    <div className="flex h-full items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.3 }}
        className="w-full max-w-md space-y-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-2xl font-bold">
              <Zap className="h-6 w-6 text-primary" />
              Quick Test
            </h2>
            <p className="mt-1 text-muted-foreground">
              Jump straight into testing. Select an agent and test type.
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={collapse}
            className="rounded-full"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Agent Selection */}
          <div className="space-y-2">
            <Label>Select Agent</Label>
            <AnimatedSelect value={selectedAgent} onValueChange={setSelectedAgent}>
              <AnimatedSelectTrigger className="h-12">
                <AnimatedSelectValue placeholder="Choose an agent..." />
              </AnimatedSelectTrigger>
              <AnimatedSelectContent>
                {agents.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    No agents yet. Create one first!
                  </div>
                ) : (
                  agents.map((agent) => (
                    <AnimatedSelectItem key={agent.id} value={agent.id} textValue={agent.name}>
                      <div className="flex items-center gap-2">
                        <Bot className="h-4 w-4" />
                        <span className="font-mono">{agent.name}</span>
                        <Badge variant="outline" className="text-[10px]">
                          {agent.mode}
                        </Badge>
                      </div>
                    </AnimatedSelectItem>
                  ))
                )}
              </AnimatedSelectContent>
            </AnimatedSelect>
          </div>

        {/* Test Type Selection */}
        <div className="space-y-2">
          <Label>Test Type</Label>
          <div className="grid grid-cols-2 gap-3">
            <motion.button
              type="button"
              onClick={() => setTestType("backtest")}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-colors",
                testType === "backtest"
                  ? "border-primary bg-primary/5"
                  : "border-border/50 hover:border-border"
              )}
            >
              <History className="h-6 w-6" />
              <span className="text-sm font-medium">Backtest</span>
              <span className="text-xs text-muted-foreground">Historical data</span>
            </motion.button>
            <motion.button
              type="button"
              onClick={() => setTestType("forward")}
              disabled={!canForwardTest && selectedAgent !== ""}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-colors",
                testType === "forward"
                  ? "border-[hsl(var(--accent-profit))] bg-[hsl(var(--accent-profit)/0.05)]"
                  : "border-border/50 hover:border-border",
                !canForwardTest && selectedAgent && "opacity-50 cursor-not-allowed"
              )}
            >
              <Play className="h-6 w-6" />
              <span className="text-sm font-medium">Forward Test</span>
              <span className="text-xs text-muted-foreground">Live paper trading</span>
            </motion.button>
          </div>
          {selectedAgent && !canForwardTest && (
            <p className="text-xs text-[hsl(var(--accent-amber))]">
              Forward testing requires at least one profitable backtest
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4">
          <Button variant="outline" onClick={collapse}>
            Cancel
          </Button>
          <motion.div
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              onClick={() => onStartTest(collapse)}
              disabled={!selectedAgent}
              className={cn(
                testType === "backtest"
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-[hsl(var(--accent-profit))] text-black hover:bg-[hsl(var(--accent-profit))]/90"
              )}
            >
              <Zap className="mr-2 h-4 w-4" />
              Start {testType === "backtest" ? "Backtest" : "Forward Test"}
            </Button>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}

