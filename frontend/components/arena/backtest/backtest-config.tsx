"use client";

import { useEffect, useMemo, useState } from "react";
import { History, Zap, Bot, Clock, DollarSign, Shield, TrendingUp } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
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
import { useArenaCatalogs } from "@/hooks/use-arena-catalogs";
import { useArenaApi } from "@/hooks/use-arena-api";

export function BacktestConfig() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedAgent = searchParams.get("agent");
  const { agents } = useAgentsStore();
  const { setBacktestConfig, seedSessionData } = useArenaStore();
  const { assets, timeframes, datePresets, playbackSpeeds, isLoading, error: catalogError } =
    useArenaCatalogs();
  const { startBacktest } = useArenaApi();

  const [config, setConfig] = useState({
    agentId: preselectedAgent || "",
    asset: "",
    timeframe: "",
    datePreset: "30d",
    startDate: "",
    endDate: "",
    capital: "10000",
    speed: "normal" as "slow" | "normal" | "fast" | "instant",
    safetyMode: true,
    allowLeverage: false,
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!config.asset && assets.length) {
      setConfig((prev) => ({ ...prev, asset: assets[0].id }));
    }
  }, [assets, config.asset]);

  useEffect(() => {
    if (!config.timeframe && timeframes.length) {
      setConfig((prev) => ({ ...prev, timeframe: timeframes[0].id }));
    }
  }, [timeframes, config.timeframe]);

  const selectedAgent = agents.find((a) => a.id === config.agentId);
  const timeframeMeta = timeframes.find((tf) => tf.id === config.timeframe);
  const presetMeta = datePresets.find((preset) => preset.id === config.datePreset);
  const playbackMeta = playbackSpeeds.find((speed) => speed.id === config.speed);
  const estimatedCandles = useMemo(() => {
    if (!timeframeMeta || !presetMeta?.days) return 0;
    const minutes = timeframeMeta.minutes || 60;
    return Math.max(1, Math.round((presetMeta.days * 24 * 60) / minutes));
  }, [timeframeMeta, presetMeta]);
  const estimatedTime = useMemo(() => {
    const msPerCandle = playbackMeta?.ms ?? 500;
    return Math.max(1, Math.ceil((estimatedCandles * msPerCandle) / 60000));
  }, [estimatedCandles, playbackMeta]);

  const handleStartBattle = async () => {
    if (!config.agentId || !config.asset || !config.timeframe) {
      setFormError("Please select an agent, asset, and timeframe.");
      return;
    }
    const usingCustomDates = config.datePreset === "custom";
    if (usingCustomDates && (!config.startDate || !config.endDate)) {
      setFormError("Please select both start and end dates for custom date range.");
      return;
    }
    if (usingCustomDates && config.startDate && config.endDate && config.startDate >= config.endDate) {
      setFormError("Start date must be before end date.");
      return;
    }
    setFormError(null);
    setIsSubmitting(true);
    try {
      const session = await startBacktest({
        agent_id: config.agentId,
        asset: config.asset,
        timeframe: config.timeframe,
        date_preset: usingCustomDates ? null : config.datePreset,
        start_date: usingCustomDates && config.startDate ? config.startDate : null,
        end_date: usingCustomDates && config.endDate ? config.endDate : null,
        starting_capital: Number(config.capital),
        playback_speed: config.speed,
        safety_mode: config.safetyMode,
        allow_leverage: config.allowLeverage,
      });

      setBacktestConfig({
        agentId: config.agentId,
        asset: config.asset,
        timeframe: config.timeframe as "15m" | "1h" | "4h" | "1d",
        datePreset: config.datePreset,
        startDate: config.startDate || undefined,
        endDate: config.endDate || undefined,
        capital: Number(config.capital),
        speed: config.speed,
        safetyMode: config.safetyMode,
        allowLeverage: config.allowLeverage,
      });
      
      if (session.previewCandles?.length) {
        seedSessionData(session.id, {
          candles: session.previewCandles,
          totalCandles: session.previewCandles.length,
          currentCandle: session.previewCandles.length - 1,
          equity: Number(config.capital),
          pnl: 0,
          status: "running",
        });
      }

      router.push(`/dashboard/arena/backtest/${session.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start backtest";
      setFormError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const canStart =
    !!config.agentId && 
    !!config.asset && 
    !!config.timeframe && 
    !!config.capital && 
    !isLoading &&
    (config.datePreset !== "custom" || (!!config.startDate && !!config.endDate));

  if (isLoading && assets.length === 0 && timeframes.length === 0) {
    return (
      <Card className="border-border/50 bg-card/30">
        <CardContent className="space-y-2 p-4 text-sm text-muted-foreground">
          Loading arena configuration...
        </CardContent>
      </Card>
    );
  }

  if (catalogError && assets.length === 0) {
    return (
      <Card className="border-destructive/40 bg-destructive/10">
        <CardContent className="space-y-2 p-4 text-sm text-destructive">
          {catalogError}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header - Compact */}
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/50">
          <History className="h-4 w-4 text-muted-foreground" />
          </div>
          <div>
          <h1 className="font-mono text-lg font-bold">Backtest Arena</h1>
          <p className="text-xs text-muted-foreground">
              Test your AI agent against historical market data
            </p>
        </div>
      </div>

      <div className="space-y-4">
          {/* Step 1: Select Agent */}
          <Card className="border-border/50 bg-card/30">
          <CardHeader className="py-2 px-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <span className="flex h-4 w-4 items-center justify-center rounded-full bg-muted text-[10px]">
                  1
                </span>
                Select Agent
              </CardTitle>
            </CardHeader>
          <CardContent className="space-y-2 px-3 pb-3">
              <AnimatedSelect
                value={config.agentId}
                onValueChange={(value) => setConfig({ ...config, agentId: value })}
              >
              <AnimatedSelectTrigger className="h-8 text-sm">
                  <AnimatedSelectValue placeholder="Select an agent..." />
                </AnimatedSelectTrigger>
                <AnimatedSelectContent>
                  {agents.map((agent) => (
                    <AnimatedSelectItem key={agent.id} value={agent.id} textValue={agent.name}>
                      <div className="flex items-center gap-3">
                        <Bot className="h-4 w-4" />
                        <span className="font-mono">{agent.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {agent.model} • {agent.mode}
                        </span>
                        <Badge variant="secondary" className="ml-auto text-xs">
                          {agent.stats.totalTests} tests
                        </Badge>
                      </div>
                    </AnimatedSelectItem>
                  ))}
                </AnimatedSelectContent>
              </AnimatedSelect>

              {selectedAgent && (
              <div className="rounded-lg border border-border/50 bg-muted/20 p-2">
                  <div className="flex items-center gap-2">
                  <Bot className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="font-mono text-xs font-medium">
                      {selectedAgent.name}
                    </span>
                    <Badge
                      variant="outline"
                      className={cn(
                      "text-[10px] h-4",
                        selectedAgent.mode === "monk"
                        ? "border-[hsl(var(--brand-lavender)/0.3)] text-[hsl(var(--brand-lavender))]"
                          : "border-primary/30 text-primary"
                      )}
                    >
                      {selectedAgent.mode}
                    </Badge>
                  </div>
                <p className="mt-0.5 text-[10px] text-muted-foreground">
                  {selectedAgent.model} • {selectedAgent.stats.totalTests} tests
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Step 2: Arena Settings */}
          <Card className="border-border/50 bg-card/30">
          <CardHeader className="py-2 px-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <span className="flex h-4 w-4 items-center justify-center rounded-full bg-muted text-[10px]">
                  2
                </span>
                Arena Settings
              </CardTitle>
            </CardHeader>
          <CardContent className="space-y-2.5 px-3 pb-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Asset</Label>
              <AnimatedSelect
                value={config.asset}
                onValueChange={(value) => setConfig({ ...config, asset: value })}
              >
                <AnimatedSelectTrigger className="h-8 text-sm">
                      <AnimatedSelectValue placeholder="Select asset" />
                    </AnimatedSelectTrigger>
                    <AnimatedSelectContent>
                      {assets.map((asset) => (
                        <AnimatedSelectItem key={asset.id} value={asset.id} textValue={asset.name}>
                          <span>
                            {asset.icon} {asset.name}
                          </span>
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
                      <AnimatedSelectValue placeholder="Select timeframe" />
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

            <div className="space-y-1.5">
              <Label className="text-xs">Date Range</Label>
              <div className="flex flex-wrap gap-1.5">
                  {datePresets.map((preset) => (
                    <Button
                      key={preset.id}
                      variant={config.datePreset === preset.id ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => setConfig({ ...config, datePreset: preset.id })}
                    className="text-xs h-7 px-2.5"
                    >
                      {preset.name}
                    </Button>
                  ))}
                </div>
              {config.datePreset === "custom" && (
                <div className="grid gap-2 sm:grid-cols-2 mt-2">
                  <div className="space-y-1">
                    <Label className="text-[10px] text-muted-foreground">Start Date</Label>
                    <Input
                      type="date"
                      value={config.startDate}
                      onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
                      className="h-7 text-xs"
                      max={new Date().toISOString().split('T')[0]}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-[10px] text-muted-foreground">End Date</Label>
                    <Input
                      type="date"
                      value={config.endDate}
                      onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
                      className="h-7 text-xs"
                      max={new Date().toISOString().split('T')[0]}
                    />
                  </div>
                </div>
              )}
              <p className="text-[10px] text-muted-foreground">
                  {config.datePreset === "custom" 
                    ? "Select start and end dates" 
                    : `~${estimatedCandles} candles • ${config.timeframe} timeframe`}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Step 3: Simulation Settings & Summary - Side by side */}
          <div className="grid gap-3 lg:grid-cols-2">
            {/* Simulation Settings */}
          <Card className="border-border/50 bg-card/30">
              <CardHeader className="py-2 px-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-muted text-[10px]">
                  3
                </span>
                Simulation Settings
              </CardTitle>
            </CardHeader>
              <CardContent className="space-y-2.5 px-3 pb-3">
              <div className="grid gap-2.5 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">Starting Capital</Label>
                  <div className="relative">
                    <DollarSign className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      type="number"
                      value={config.capital}
                      onChange={(e) => setConfig({ ...config, capital: e.target.value })}
                      className="pl-8 font-mono text-sm h-8"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">Playback Speed</Label>
                  <AnimatedSelect
                    value={config.speed}
                    onValueChange={(value) =>
                      setConfig({ ...config, speed: value as typeof config.speed })
                    }
                  >
                    <AnimatedSelectTrigger className="text-sm h-8">
                      <AnimatedSelectValue placeholder="Select speed" />
                    </AnimatedSelectTrigger>
                    <AnimatedSelectContent>
                      {playbackSpeeds.map((speed) => (
                        <AnimatedSelectItem key={speed.id} value={speed.id} textValue={speed.name}>
                          {speed.name}
                        </AnimatedSelectItem>
                      ))}
                    </AnimatedSelectContent>
                  </AnimatedSelect>
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="safety"
                    checked={config.safetyMode}
                    onCheckedChange={(checked) =>
                      setConfig({ ...config, safetyMode: checked as boolean })
                    }
                  />
                  <Label htmlFor="safety" className="flex items-center gap-1.5 text-[10px] font-normal">
                    <Shield className="h-3 w-3 text-muted-foreground" />
                    Safety Mode (Auto stop-loss -2%)
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="leverage"
                    checked={config.allowLeverage}
                    onCheckedChange={(checked) =>
                      setConfig({ ...config, allowLeverage: checked as boolean })
                    }
                  />
                  <Label htmlFor="leverage" className="flex items-center gap-1.5 text-[10px] font-normal">
                    <TrendingUp className="h-3 w-3 text-muted-foreground" />
                    Allow Leverage (Up to 5x)
                  </Label>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Battle Summary */}
          <Card className="border-border/50 bg-card/30">
            <CardHeader className="py-2 px-3">
              <CardTitle className="text-sm">Battle Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 px-3 pb-3">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-[10px]">Agent</span>
                  <span className="font-mono text-[10px]">{selectedAgent?.name || "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-[10px]">Asset</span>
                  <span className="font-mono text-[10px]">
                    {assets.find((a) => a.id === config.asset)?.name || "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-[10px]">Period</span>
                  <span className="font-mono text-[10px]">
                    {presetMeta?.name ?? "Custom"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-[10px]">Capital</span>
                  <span className="font-mono text-[10px]">${parseInt(config.capital).toLocaleString()}</span>
                </div>
              </div>

              <div className="rounded-lg border border-border/50 bg-muted/20 p-2">
                <div className="flex items-center gap-1.5 text-[10px]">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  <span className="text-muted-foreground">Est. time:</span>
                  <span className="font-mono font-medium">
                    {estimatedTime ? `~${estimatedTime} min` : "Pending"}
                  </span>
                </div>
              </div>

              {formError && (
                <p className="text-[10px] text-destructive">{formError}</p>
              )}

              <Button
                className="w-full gap-2 bg-primary text-primary-foreground hover:bg-primary/90 h-8 text-xs"
                disabled={!canStart || isSubmitting}
                onClick={handleStartBattle}
              >
                <Zap className="h-3.5 w-3.5" />
                {isSubmitting ? "Starting..." : "Start Battle"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

