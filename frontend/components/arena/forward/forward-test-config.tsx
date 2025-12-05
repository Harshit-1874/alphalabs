"use client";

import { useEffect, useState } from "react";
import { Play, Bot, DollarSign, Shield, Bell, CheckCircle, XCircle, ArrowRight, Info, Brain } from "lucide-react";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { useAgentsStore, useArenaStore } from "@/lib/stores";
import { useApiClient } from "@/lib/api";
import { useArenaApi } from "@/hooks/use-arena-api";
import { useAgents } from "@/hooks/use-agents";
import type { Asset, Timeframe } from "@/types/arena";

export function ForwardTestConfig() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedAgent = searchParams.get("agent");
  
  // Get agents from store
  const { agents } = useAgentsStore();
  // Ensure agents are loaded when component mounts
  useAgents();
  const { setForwardConfig } = useArenaStore();
  const { get } = useApiClient();
  const { startForwardTest } = useArenaApi();

  const [assets, setAssets] = useState<Asset[]>([]);
  const [timeframes, setTimeframes] = useState<Timeframe[]>([]);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [configError, setConfigError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const [config, setConfig] = useState({
    agentId: preselectedAgent || "",
    asset: "btc-usdt",
    timeframe: "1h",
    capital: "10000",
    safetyMode: true,
    emailNotifications: false,
    autoStopOnLoss: false,
    decisionMode: "every_candle" as "every_candle" | "every_n_candles",
    decisionInterval: "1",
  });

  const selectedAgent = agents.find((a) => a.id === config.agentId);
  // Check if agent has at least one profitable backtest
  const profitableTests = selectedAgent?.stats.profitableTests ?? 0;
  const configReady = !isLoadingConfig && assets.length > 0 && timeframes.length > 0;
  const canForwardTest = selectedAgent && profitableTests > 0;
  const canStartForward = canForwardTest && configReady && !isStarting;

  useEffect(() => {
    let active = true;
    setIsLoadingConfig(true);
    setConfigError(null);

    void Promise.all([
      get<{ assets: Asset[] }>("/api/data/assets"),
      get<{ timeframes: Timeframe[] }>("/api/data/timeframes"),
    ])
      .then(([assetsRes, timeframesRes]) => {
        if (!active) return;
        setAssets(assetsRes.assets);
        setTimeframes(timeframesRes.timeframes);
        if (!assetsRes.assets.length && !config.asset) {
          setConfig((prev) => ({ ...prev, asset: assetsRes.assets[0]?.id ?? prev.asset }));
        }
        if (!timeframesRes.timeframes.length && !config.timeframe) {
          setConfig((prev) => ({ ...prev, timeframe: timeframesRes.timeframes[0]?.id ?? prev.timeframe }));
        }
      })
      .catch((err) => {
        if (!active) return;
        setConfigError(err instanceof Error ? err.message : "Failed to load arena config");
      })
      .finally(() => {
        if (!active) return;
        setIsLoadingConfig(false);
      });

    return () => {
      active = false;
    };
  }, [get]);

  const handleStartTest = async () => {
    if (!config.agentId || isStarting) return;

    setIsStarting(true);
    setStartError(null);

    try {
      const response = await startForwardTest({
        agent_id: config.agentId,
        asset: config.asset,
        timeframe: config.timeframe,
        starting_capital: parseInt(config.capital, 10),
        safety_mode: config.safetyMode,
        email_notifications: config.emailNotifications,
        auto_stop_on_loss: config.autoStopOnLoss,
        auto_stop_loss_pct: config.autoStopOnLoss ? 10 : 0,
        allow_leverage: false,
        decision_mode: config.decisionMode,
        decision_interval_candles: Number(config.decisionInterval || "1"),
      });

      setForwardConfig({
        agentId: config.agentId,
        asset: config.asset,
        timeframe: config.timeframe,
        capital: parseInt(config.capital, 10),
        safetyMode: config.safetyMode,
        emailNotifications: config.emailNotifications,
        autoStopOnLoss: config.autoStopOnLoss,
      });

      router.push(`/dashboard/arena/forward/${response.id}`);
    } catch (err) {
      setStartError(err instanceof Error ? err.message : "Failed to start forward test");
    } finally {
      setIsStarting(false);
    }
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
      {configError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {configError}
        </div>
      )}

      {/* Council Mode Coming Soon Banner */}
      <Alert className="border-purple-500/20 bg-gradient-to-r from-purple-500/5 via-blue-500/5 to-purple-500/5">
        <Brain className="h-4 w-4 text-purple-400" />
        <AlertDescription className="text-sm">
          <div className="flex items-center justify-between">
            <div>
              <span className="font-semibold text-foreground">🧠 Council Mode for Forward Testing</span>
              <span className="text-muted-foreground"> — Coming Soon!</span>
            </div>
            <Link href="/dashboard/arena/backtest">
              <Button variant="outline" size="sm" className="ml-4 border-purple-500/30 hover:bg-purple-500/10">
                Try it in Backtest
                <ArrowRight className="ml-2 h-3 w-3" />
              </Button>
            </Link>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Multiple AI models will soon collaborate on live trading decisions for more robust analysis.
          </p>
        </AlertDescription>
      </Alert>

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
                      {assets.length === 0 ? (
                        <AnimatedSelectItem value="" disabled>
                          Loading assets...
                        </AnimatedSelectItem>
                      ) : (
                        assets.map((asset) => (
                          <AnimatedSelectItem key={asset.id} value={asset.id} textValue={asset.name}>
                            {asset.icon} {asset.name}
                          </AnimatedSelectItem>
                        ))
                      )}
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
                      {timeframes.length === 0 ? (
                        <AnimatedSelectItem value="" disabled>
                          Loading timeframes...
                        </AnimatedSelectItem>
                      ) : (
                        timeframes.map((tf) => (
                          <AnimatedSelectItem key={tf.id} value={tf.id} textValue={tf.name}>
                            {tf.name}
                          </AnimatedSelectItem>
                        ))
                      )}
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

            <div className="space-y-1.5">
              <Label className="text-xs">Decision Cadence</Label>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={config.decisionMode === "every_candle" ? "secondary" : "outline"}
                  size="sm"
                  className="text-[10px] px-3 h-8"
                  onClick={() => setConfig({ ...config, decisionMode: "every_candle" })}
                >
                  Every candle
                </Button>
                <Button
                  variant={config.decisionMode === "every_n_candles" ? "secondary" : "outline"}
                  size="sm"
                  className="text-[10px] px-3 h-8"
                  onClick={() => setConfig({ ...config, decisionMode: "every_n_candles" })}
                >
                  Every N candles
                </Button>
              </div>
              {config.decisionMode === "every_n_candles" && (
                <div className="flex flex-col gap-1">
                  <Input
                    type="number"
                    min={1}
                    value={config.decisionInterval}
                    onChange={(e) => setConfig({ ...config, decisionInterval: e.target.value })}
                    className="h-8 text-sm"
                    placeholder="Interval (e.g., 4)"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Enter how many candles between AI interventions (e.g., 4 means every 4th candle).
                  </p>
                </div>
              )}
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
                  {assets.find((a) => a.id === config.asset)?.name ?? "—"}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 bg-muted/20 p-2">
                  <p className="text-[10px] text-muted-foreground">Timeframe</p>
                  <p className="font-mono text-xs font-medium">
                  {timeframes.find((t) => t.id === config.timeframe)?.name ?? "—"}
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
                disabled={!canStartForward}
                onClick={handleStartTest}
              >
                <Play className="h-4 w-4" />
                {isStarting ? "Starting…" : "Start Forward Test"}
              </Button>
              {startError && (
                <p className="mt-2 text-[10px] text-destructive text-center">
                  {startError}
                </p>
              )}
              {!configReady && (
                <p className="mt-2 text-[10px] text-muted-foreground text-center">
                  Loading arena configuration...
                </p>
              )}

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

