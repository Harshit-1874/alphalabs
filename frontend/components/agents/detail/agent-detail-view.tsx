"use client";

import { useState } from "react";
import { ChevronLeft, Edit, History, Play, MoreVertical, Copy, FileDown, Trash2, Bot } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  AnimatedDropdown,
  AnimatedDropdownContent,
  AnimatedDropdownItem,
  AnimatedDropdownSeparator,
  AnimatedDropdownTrigger,
} from "@/components/ui/animated-dropdown";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useAgents } from "@/hooks/use-agents";
import { useAgentsStore } from "@/lib/stores";
import { DeleteAgentDialog } from "../delete-agent-dialog";
import type { AgentDetailViewProps, Agent, AgentStats } from "@/types/agent";

// Mock data - in real app from API
const mockAgent: Agent = {
  id: "1",
  name: "α-1",
  model: "DeepSeek-R1",
  mode: "monk",
  indicators: ["RSI", "MACD", "EMA", "ATR", "Volume", "Stochastic", "CCI", "ADX"],
  customIndicators: [{ name: "Secret_Sauce", formula: "(close - sma_50) / atr_14" }],
  strategyPrompt: `My trading philosophy:

1. Only enter LONG positions when RSI is below 30 (oversold) AND MACD histogram is turning positive (momentum shift).

2. Only enter SHORT positions when RSI is above 70 (overbought) AND price is below EMA_50 (bearish trend).

3. Always set stop loss at 1.5x ATR below entry for LONG, above entry for SHORT.

4. Take profit at 2x the stop loss distance (2:1 R:R).

5. If uncertain, HOLD. Capital preservation is priority.`,
  apiKeyMasked: "sk-or-v1-••••••••",
  testsRun: 12,
  bestPnL: 47.2,
  createdAt: new Date("2025-11-15"),
  updatedAt: new Date("2025-11-24"),
  isArchived: false,
  stats: {
    totalTests: 12,
    profitableTests: 7,
    bestPnL: 47.2,
    avgWinRate: 58,
    avgDrawdown: -8.3,
  } as AgentStats,
};

export function AgentDetailView({ agentId }: AgentDetailViewProps) {
  const router = useRouter();
  const { agents } = useAgentsStore();
  const { duplicateAgent } = useAgents();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDuplicating, setIsDuplicating] = useState(false);

  // Find the actual agent from store
  const agent = agents.find((a) => a.id === agentId);
  
  // Fallback to mock if not found (for development)
  const displayAgent = agent || mockAgent;

  const handleDuplicate = async () => {
    if (isDuplicating || !agent) {
      if (!agent) {
        toast.error("Agent not found");
      }
      return;
    }
    
    setIsDuplicating(true);
    try {
      const newName = `${agent.name} (Copy)`;
      const duplicated = await duplicateAgent(agentId, newName);
      toast.success(`Agent "${newName}" created successfully!`);
      router.push(`/dashboard/agents/${duplicated.id}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to duplicate agent";
      toast.error(errorMessage);
    } finally {
      setIsDuplicating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/dashboard/agents"
          className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Agents
        </Link>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          {/* Agent Info */}
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted/50">
              <Bot className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-mono text-2xl font-bold">{displayAgent.name}</h1>
                <Badge
                  variant="outline"
                  className={cn(
                    displayAgent.mode === "monk"
                      ? "border-[hsl(var(--brand-lavender)/0.3)] text-[hsl(var(--brand-lavender))]"
                      : "border-primary/30 text-primary"
                  )}
                >
                  {displayAgent.mode === "monk" ? "Monk" : "Omni"}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {displayAgent.model} • Created{" "}
                {displayAgent.createdAt.toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/dashboard/agents/${agentId}/edit`)}
            >
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/dashboard/arena/backtest?agent=${agentId}`)}
            >
              <History className="mr-2 h-4 w-4" />
              Backtest
            </Button>
            <Button
              size="sm"
              className="bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => router.push(`/dashboard/arena/forward?agent=${agentId}`)}
            >
              <Play className="mr-2 h-4 w-4" />
              Forward Test
            </Button>
            <AnimatedDropdown>
              <AnimatedDropdownTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </AnimatedDropdownTrigger>
              <AnimatedDropdownContent align="end">
                <AnimatedDropdownItem 
                  onSelect={handleDuplicate}
                  disabled={isDuplicating || !agent}
                >
                  <Copy className="mr-2 h-4 w-4" />
                  {isDuplicating ? "Duplicating..." : "Duplicate"}
                </AnimatedDropdownItem>
                <AnimatedDropdownItem onSelect={() => toast.info("Export coming soon")}>
                  <FileDown className="mr-2 h-4 w-4" />
                  Export Config
                </AnimatedDropdownItem>
                <AnimatedDropdownSeparator />
                <AnimatedDropdownItem 
                  destructive
                  onSelect={() => setShowDeleteDialog(true)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </AnimatedDropdownItem>
              </AnimatedDropdownContent>
            </AnimatedDropdown>
          </div>

          {/* Delete Confirmation Dialog */}
          <DeleteAgentDialog
            agentId={agentId}
            agentName={displayAgent.name}
            open={showDeleteDialog}
            onOpenChange={setShowDeleteDialog}
            isArchived={displayAgent.isArchived}
          />
        </div>
      </div>

      {/* Performance Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Total Tests</p>
            <p className="mt-1 font-mono text-2xl font-bold">{displayAgent.stats.totalTests}</p>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Best PnL</p>
            <p className="mt-1 font-mono text-2xl font-bold text-[hsl(var(--accent-profit))]">
              +{displayAgent.stats.bestPnL}%
            </p>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Win Rate</p>
            <p className="mt-1 font-mono text-2xl font-bold">{displayAgent.stats.avgWinRate}%</p>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Avg Drawdown</p>
            <p className="mt-1 font-mono text-2xl font-bold text-[hsl(var(--accent-red))]">
              {displayAgent.stats.avgDrawdown}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="configuration">Configuration</TabsTrigger>
          <TabsTrigger value="history">Test History</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6 space-y-6">
          {/* Strategy Summary */}
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="text-base">Strategy Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap font-mono text-sm text-muted-foreground">
                {displayAgent.strategyPrompt.slice(0, 300)}...
              </p>
              <Button variant="link" className="mt-2 h-auto p-0 text-xs">
                Show Full Strategy
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="configuration" className="mt-6 space-y-6">
          {/* Identity */}
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="text-base">Identity</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Name</span>
                <span className="font-mono text-sm">{displayAgent.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Mode</span>
                <Badge
                  variant="outline"
                  className={cn(
                    displayAgent.mode === "monk"
                      ? "border-[hsl(var(--brand-lavender)/0.3)] text-[hsl(var(--brand-lavender))]"
                      : "border-primary/30 text-primary"
                  )}
                >
                  {displayAgent.mode === "monk" ? "🧘 Monk Mode" : "👁️ Omni Mode"}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Created</span>
                <span className="text-sm">{displayAgent.createdAt.toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Last Updated</span>
                <span className="text-sm">{displayAgent.updatedAt.toLocaleDateString()}</span>
              </div>
            </CardContent>
          </Card>

          {/* Model & API */}
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="text-base">Model & API</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Model</span>
                <span className="font-mono text-sm">{displayAgent.model}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">API Key</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm">{displayAgent.apiKeyMasked}</span>
                  <Button variant="ghost" size="sm" className="h-6 text-xs">
                    Reveal
                  </Button>
                  <Button variant="ghost" size="sm" className="h-6 text-xs">
                    Test
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Data Sources */}
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="text-base">Data Sources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="mb-2 text-sm text-muted-foreground">
                  Indicators ({displayAgent.indicators.length})
                </p>
                {/* Horizontally scrollable indicator tags */}
                <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
                  {displayAgent.indicators.map((ind) => (
                    <Badge key={ind} variant="secondary" className="shrink-0">
                      {ind}
                    </Badge>
                  ))}
                </div>
              </div>
              {displayAgent.customIndicators.length > 0 && (
                <div>
                  <p className="mb-2 text-sm text-muted-foreground">
                    Custom Indicators ({displayAgent.customIndicators.length})
                  </p>
                  {displayAgent.customIndicators.map((ind) => (
                    <div
                      key={ind.name}
                      className="rounded-lg border border-border/50 bg-muted/20 p-3"
                    >
                      <p className="font-mono text-sm font-medium">{ind.name}</p>
                      <p className="font-mono text-xs text-muted-foreground">
                        {ind.formula}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Strategy Prompt */}
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="text-base">Strategy Prompt</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap rounded-lg border border-border/50 bg-muted/20 p-4 font-mono text-sm text-muted-foreground">
                {displayAgent.strategyPrompt}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-6">
          <Card className="border-border/50 bg-card/30">
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <History className="mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="font-mono text-lg font-medium">Test history</h3>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Run backtests or forward tests to see results here.
              </p>
              <Button asChild className="mt-4">
                <Link href={`/dashboard/arena/backtest?agent=${agentId}`}>
                  Start Backtest
                </Link>
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

