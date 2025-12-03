"use client";

import { useState } from "react";
import { Play, Bot, DollarSign, Shield, Bell, CheckCircle, XCircle, ArrowRight } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AnimatedSelect,
  AnimatedSelectContent,
  AnimatedSelectItem,
  AnimatedSelectTrigger,
  AnimatedSelectValue,
} from "@/components/ui/animated-select";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAgentsStore, useArenaStore } from "@/lib/stores";

const assets = [
  { id: "btc-usdt", name: "BTC/USDT", icon: "₿" },
  { id: "eth-usdt", name: "ETH/USDT", icon: "Ξ" },
  { id: "sol-usdt", name: "SOL/USDT", icon: "◎" },
];

const timeframes = [
  { id: "15m", name: "15 Minutes" },
  { id: "1h", name: "1 Hour" },
  { id: "4h", name: "4 Hours" },
];

// Mock active sessions
const mockActiveSessions: Array<{
  id: string;
  agentName: string;
  asset: string;
  duration: string;
  pnl: number;
}> = [];

export function ForwardTestConfig() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedAgent = searchParams.get("agent");
  
  // Get agents from store
  const { agents } = useAgentsStore();
  const { setForwardConfig } = useArenaStore();

  const [config, setConfig] = useState({
    agentId: preselectedAgent || "",
    asset: "btc-usdt",
    timeframe: "1h",
    capital: "10000",
    safetyMode: true,
    emailNotifications: false,
    autoStopOnLoss: false,
  });

  const selectedAgent = agents.find((a) => a.id === config.agentId);
  // Check if agent has at least one profitable backtest
  const profitableTests = selectedAgent?.stats.profitableTests ?? 0;
  const canForwardTest = selectedAgent && profitableTests > 0;

  const handleStartTest = () => {
    // Save config to store before navigating
    setForwardConfig({
      agentId: config.agentId,
      asset: config.asset,
      timeframe: config.timeframe as "15m" | "1h" | "4h",
      capital: parseInt(config.capital),
      safetyMode: config.safetyMode,
      emailNotifications: config.emailNotifications,
      autoStopOnLoss: config.autoStopOnLoss,
    });
    
    const sessionId = Math.random().toString(36).substring(7);
    router.push(`/dashboard/arena/forward/${sessionId}`);
  };

  return (
    <div className="space-y-4">
      {/* Header - Compact */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[hsl(var(--accent-green)/0.15)]">
            <Play className="h-4 w-4 text-[hsl(var(--accent-green))]" />
          </div>
          <div>
            <h1 className="font-mono text-lg font-bold">Forward Test Arena</h1>
            <p className="text-xs text-muted-foreground">
              Paper trade with live market data - no real money at risk
            </p>
          </div>
        </div>
        <Badge variant="outline" className="w-fit border-[hsl(var(--accent-green)/0.3)] text-[hsl(var(--accent-green))] text-xs h-6">
          <span className="mr-1 h-1.5 w-1.5 rounded-full bg-[hsl(var(--accent-green))] animate-pulse" />
          LIVE DATA
        </Badge>
      </div>

      {/* Agent Selection - Compact */}
      <Card className="border-border/50 bg-gradient-to-r from-[hsl(var(--accent-green)/0.05)] to-transparent">
        <CardContent className="p-3">
          <div className="flex flex-col lg:flex-row lg:items-center gap-3">
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-xs font-medium text-muted-foreground">Select Your Agent</p>
                <p className="text-[10px] text-muted-foreground/70">Must have profitable backtest</p>
              </div>
              </div>
            <div className="flex-1 lg:max-w-md">
              <AnimatedSelect
                value={config.agentId}
                onValueChange={(value) => setConfig({ ...config, agentId: value })}
              >
                <AnimatedSelectTrigger className="h-8 text-sm">
                  <AnimatedSelectValue placeholder="Select an agent..." />
                </AnimatedSelectTrigger>
                <AnimatedSelectContent>
                  {agents.map((agent) => {
                    const agentProfitableTests = agent.stats.profitableTests ?? 0;
                    return (
                      <AnimatedSelectItem
                        key={agent.id}
                        value={agent.id}
                        textValue={agent.name}
                        disabled={agentProfitableTests === 0}
                      >
                        <div className="flex items-center gap-3">
                          <Bot className="h-4 w-4" />
                          <span className="font-mono">{agent.name}</span>
                          {agentProfitableTests > 0 ? (
                            <Badge variant="secondary" className="text-xs text-[hsl(var(--accent-green))]">
                              ✓ {agentProfitableTests} profitable
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-xs text-[hsl(var(--accent-red))]">
                              ✗ No profitable tests
                            </Badge>
                          )}
                        </div>
                      </AnimatedSelectItem>
                    );
                  })}
                </AnimatedSelectContent>
              </AnimatedSelect>
            </div>
            {selectedAgent && (
              <div className="flex items-center gap-2 rounded-lg border border-[hsl(var(--accent-green)/0.3)] bg-[hsl(var(--accent-green)/0.1)] px-3 py-1.5">
                <div className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--accent-green))]" />
                <span className="font-mono text-xs font-medium">{selectedAgent.name}</span>
                <span className="text-[10px] text-muted-foreground">Ready to trade</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Config Grid */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Requirements Check */}
        <Card className="border-border/50 bg-card/30">
          <CardHeader className="py-2 px-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <CheckCircle className="h-3.5 w-3.5 text-muted-foreground" />
              Requirements
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 px-3 pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-[hsl(var(--accent-green))]" />
              <span className="text-xs">Valid API key configured</span>
            </div>
            <div className="flex items-center gap-2">
              {profitableTests > 0 ? (
                <CheckCircle className="h-3.5 w-3.5 text-[hsl(var(--accent-green))]" />
              ) : (
                <XCircle className="h-3.5 w-3.5 text-[hsl(var(--accent-red))]" />
              )}
              <span className="text-xs">Profitable backtest</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3.5 w-3.5 text-[hsl(var(--accent-green))]" />
              <span className="text-xs">Account verified</span>
            </div>
            </CardContent>
          </Card>

        {/* Market Settings */}
          <Card className="border-border/50 bg-card/30">
          <CardHeader className="py-2 px-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
              Market Settings
            </CardTitle>
            </CardHeader>
          <CardContent className="space-y-2.5 px-3 pb-3">
            <div className="grid gap-2.5 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Asset</Label>
                  <AnimatedSelect
                    value={config.asset}
                    onValueChange={(value) => setConfig({ ...config, asset: value })}
                  >
                  <AnimatedSelectTrigger className="h-8 text-sm">
                      <AnimatedSelectValue />
                    </AnimatedSelectTrigger>
                    <AnimatedSelectContent>
                      {assets.map((asset) => (
                        <AnimatedSelectItem key={asset.id} value={asset.id} textValue={asset.name}>
                          {asset.icon} {asset.name}
                        </AnimatedSelectItem>
                      ))}
                    </AnimatedSelectContent>
                  </AnimatedSelect>
                </div>

              <div className="space-y-1.5">
                <Label className="text-xs">Timeframe</Label>
                  <AnimatedSelect
                    value={config.timeframe}
                    onValueChange={(value) => setConfig({ ...config, timeframe: value })}
                  >
                  <AnimatedSelectTrigger className="h-8 text-sm">
                      <AnimatedSelectValue />
                    </AnimatedSelectTrigger>
                    <AnimatedSelectContent>
                      {timeframes.map((tf) => (
                        <AnimatedSelectItem key={tf.id} value={tf.id} textValue={tf.name}>
                          {tf.name}
                        </AnimatedSelectItem>
                      ))}
                    </AnimatedSelectContent>
                  </AnimatedSelect>
                </div>
              </div>
          </CardContent>
        </Card>

        {/* Capital & Options */}
        <Card className="border-border/50 bg-card/30 lg:col-span-2">
          <CardHeader className="py-2 px-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
              Capital & Options
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 px-3 pb-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Starting Capital (Paper)</Label>
              <div className="relative max-w-xs">
                <DollarSign className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    type="number"
                    value={config.capital}
                    onChange={(e) => setConfig({ ...config, capital: e.target.value })}
                  className="pl-8 font-mono text-sm h-8"
                  />
                </div>
              </div>

            <div className="grid gap-2 sm:grid-cols-3">
              <div className="flex items-center space-x-2 rounded-lg border border-border/50 p-2">
                  <Checkbox
                    id="safety"
                    checked={config.safetyMode}
                    onCheckedChange={(checked) =>
                      setConfig({ ...config, safetyMode: checked as boolean })
                    }
                  />
                <Label htmlFor="safety" className="flex items-center gap-1.5 text-[10px] cursor-pointer font-normal">
                  <Shield className="h-3 w-3 text-muted-foreground" />
                  Safety Mode
                  </Label>
                </div>

              <div className="flex items-center space-x-2 rounded-lg border border-border/50 p-2">
                  <Checkbox
                    id="email"
                    checked={config.emailNotifications}
                    onCheckedChange={(checked) =>
                      setConfig({ ...config, emailNotifications: checked as boolean })
                    }
                  />
                <Label htmlFor="email" className="flex items-center gap-1.5 text-[10px] cursor-pointer font-normal">
                  <Bell className="h-3 w-3 text-muted-foreground" />
                  Email Alerts
                  </Label>
                </div>

              <div className="flex items-center space-x-2 rounded-lg border border-border/50 p-2">
                  <Checkbox
                    id="autostop"
                    checked={config.autoStopOnLoss}
                    onCheckedChange={(checked) =>
                      setConfig({ ...config, autoStopOnLoss: checked as boolean })
                    }
                  />
                <Label htmlFor="autostop" className="text-[10px] cursor-pointer font-normal">
                  Auto-stop at -10%
                  </Label>
                </div>
              </div>
            </CardContent>
          </Card>

        {/* Session Summary */}
        <Card className="border-border/50 bg-card/30 lg:col-span-2">
          <CardHeader className="py-2 px-3">
            <CardTitle className="text-sm">Session Summary</CardTitle>
              </CardHeader>
          <CardContent className="space-y-3 px-3 pb-3">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg border border-border/50 bg-muted/20 p-2">
                  <p className="text-[10px] text-muted-foreground">Agent</p>
                  <p className="font-mono text-xs font-medium truncate">{selectedAgent?.name || "—"}</p>
                </div>
                <div className="rounded-lg border border-border/50 bg-muted/20 p-2">
                  <p className="text-[10px] text-muted-foreground">Asset</p>
                  <p className="font-mono text-xs font-medium">
                    {assets.find((a) => a.id === config.asset)?.name}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 bg-muted/20 p-2">
                  <p className="text-[10px] text-muted-foreground">Timeframe</p>
                  <p className="font-mono text-xs font-medium">
                    {timeframes.find((t) => t.id === config.timeframe)?.name}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 bg-muted/20 p-2">
                  <p className="text-[10px] text-muted-foreground">Capital</p>
                  <p className="font-mono text-xs font-medium">${parseInt(config.capital).toLocaleString()}</p>
                </div>
              </div>

              {/* Warning */}
              <div className="rounded-lg border border-[hsl(var(--accent-amber)/0.3)] bg-[hsl(var(--accent-amber)/0.1)] p-2.5">
                <p className="text-[10px] text-[hsl(var(--accent-amber))]">
                  ⚠ This runs continuously on our servers. You can close this page and return anytime.
                </p>
              </div>

              {/* Start Button */}
              <Button
                className="w-full h-9 gap-2 text-sm bg-[hsl(var(--accent-green))] text-black hover:bg-[hsl(var(--accent-green))]/90"
                disabled={!canForwardTest}
                onClick={handleStartTest}
              >
                <Play className="h-4 w-4" />
                Start Forward Test
              </Button>

              {!canForwardTest && selectedAgent && (
                <p className="text-center text-[10px] text-[hsl(var(--accent-red))]">
                  This agent needs at least one profitable backtest first
                </p>
              )}
              {!selectedAgent && (
                <p className="text-center text-[10px] text-muted-foreground">
                  Select an agent to start
                </p>
              )}
            </CardContent>
          </Card>
      </div>
    </div>
  );
}

