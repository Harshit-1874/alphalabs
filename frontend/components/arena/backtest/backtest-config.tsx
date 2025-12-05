"use client";

import { useEffect, useMemo, useState } from "react";
import { History, Zap, Bot, Clock, DollarSign, Shield, TrendingUp, Info, ChevronDown, ChevronUp, Brain, Sparkles, X, Check } from "lucide-react";
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
import { useAgents } from "@/hooks/use-agents";
import { useModels } from "@/hooks/use-models";
import { CouncilModeBanner } from "@/components/arena/council-mode-banner";

export function BacktestConfig() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedAgent = searchParams.get("agent");
  const { agents } = useAgentsStore();
  // Ensure agents are loaded when component mounts
  useAgents();
  const { setBacktestConfig, seedSessionData } = useArenaStore();
  const { assets, timeframes, datePresets, playbackSpeeds, isLoading, error: catalogError } =
    useArenaCatalogs();
  const { startBacktest } = useArenaApi();
  const { models: allModels } = useModels();
  
  // Filter to only free models for council mode
  const freeModels = useMemo(() => 
    allModels.filter(m => m.isFree).sort((a, b) => a.name.localeCompare(b.name)),
    [allModels]
  );

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
    decisionMode: "every_candle" as "every_candle" | "every_n_candles",
    decisionInterval: "1",
    indicatorReadinessThreshold: "80", // Percentage of indicators that must be ready
    // Council Mode - IMPORTANT: councilModels are ADDITIONAL models (bot's model is auto-included)
    councilMode: false,
    councilModels: [] as string[], // Additional models to join the bot's model
    councilChairmanModel: "",
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showCouncilBanner, setShowCouncilBanner] = useState(true);
  const [showCouncilConfig, setShowCouncilConfig] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Default free council models (excluding the bot's model - it's auto-included)
  const DEFAULT_ADDITIONAL_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "google/gemma-3-27b-it:free"
  ];
  // Default chairman - use Hermes 405B for synthesis (large model, good at reasoning)
  const DEFAULT_CHAIRMAN = "nousresearch/hermes-3-llama-3.1-405b:free";

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
    if (config.councilMode && (!config.councilModels || config.councilModels.length < 1)) {
      setFormError("Council mode requires at least 1 additional model selected.");
      return;
    }
    if (config.councilMode && !config.councilChairmanModel) {
      setFormError("Please select a chairman model for the council.");
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
        decision_mode: config.decisionMode,
        decision_interval_candles: Number(config.decisionInterval || "1"),
        indicator_readiness_threshold: Number(config.indicatorReadinessThreshold || "80"),
        council_mode: config.councilMode,
        council_models: config.councilMode ? config.councilModels : null,
        council_chairman_model: config.councilMode ? config.councilChairmanModel : null,
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
        decisionMode: config.decisionMode,
        decisionIntervalCandles: Number(config.decisionInterval || "1"),
        safetyMode: config.safetyMode,
        allowLeverage: config.allowLeverage,
        councilMode: config.councilMode,
        councilModels: config.councilModels,
        councilChairmanModel: config.councilChairmanModel,
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

      {/* Council Mode Promotional Banner */}
      {showCouncilBanner && !config.councilMode && (
        <CouncilModeBanner
          onEnableCouncilMode={() => {
            setConfig(prev => ({
              ...prev,
              councilMode: true,
              councilModels: DEFAULT_ADDITIONAL_MODELS,
              councilChairmanModel: DEFAULT_CHAIRMAN
            }));
            setShowCouncilConfig(true);
            setShowCouncilBanner(false);
          }}
          onDismiss={() => setShowCouncilBanner(false)}
        />
      )}

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

                {/* <div className="space-y-1.5">
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
                </div> */}
            <div className="space-y-1.5">
              <Label className="text-xs">Decision cadence</Label>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={config.decisionMode === "every_candle" ? "secondary" : "outline"}
                  size="sm"
                  className="text-[10px] px-3"
                  onClick={() => setConfig({ ...config, decisionMode: "every_candle" })}
                >
                  Every candle
                </Button>
                <Button
                  variant={config.decisionMode === "every_n_candles" ? "secondary" : "outline"}
                  size="sm"
                  className="text-[10px] px-3"
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
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Enter how many candles between AI interventions (e.g., 4 means every 4th candle).
                  </p>
                </div>
              )}
            </div>
              </div>

              {/* Indicator Readiness Info */}
              {selectedAgent && selectedAgent.indicators && selectedAgent.indicators.length > 0 && (
                <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-2.5">
                  <div className="flex items-start gap-2">
                    <Info className="h-3.5 w-3.5 text-blue-500 mt-0.5 shrink-0" />
                    <div className="flex-1 space-y-1">
                      <p className="text-[10px] font-medium text-blue-500">
                        Indicator Warm-up Period
                      </p>
                      <p className="text-[10px] text-muted-foreground leading-relaxed">
                        Trading decisions start when {config.indicatorReadinessThreshold}% of your {selectedAgent.indicators.length} selected indicators are ready. 
                        Long-period indicators (e.g., EMA/SMA 200) may need 200+ candles to warm up.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Advanced Settings Toggle */}
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex w-full items-center justify-between rounded-lg border border-border/50 bg-muted/10 px-2 py-1.5 text-[10px] hover:bg-muted/20 transition-colors"
              >
                <span className="text-muted-foreground">Advanced Settings</span>
                {showAdvanced ? (
                  <ChevronUp className="h-3 w-3 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-3 w-3 text-muted-foreground" />
                )}
              </button>

              {/* Advanced Settings Content */}
              {showAdvanced && (
                <div className="space-y-2 rounded-lg border border-border/50 bg-muted/10 p-2.5">
                  <div className="space-y-1.5">
                    <Label className="text-xs flex items-center gap-1.5">
                      <Info className="h-3 w-3 text-muted-foreground" />
                      Indicator Readiness Threshold (%)
                    </Label>
                    <Input
                      type="number"
                      min={50}
                      max={100}
                      value={config.indicatorReadinessThreshold}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === "" || (parseInt(val) >= 50 && parseInt(val) <= 100)) {
                          setConfig({ ...config, indicatorReadinessThreshold: val });
                        }
                      }}
                      className="h-8 text-sm"
                    />
                    <p className="text-[10px] text-muted-foreground">
                      Minimum percentage of indicators that must be ready before trading starts (50-100%). 
                      Lower = start earlier but with fewer indicators. Default: 80%
                    </p>
                  </div>
                </div>
              )}

              {/* Council Mode Section */}
              <div className="space-y-2 rounded-lg border-2 border-purple-500/30 bg-gradient-to-r from-purple-500/5 via-blue-500/5 to-purple-500/5 p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="council-mode"
                      checked={config.councilMode}
                      onCheckedChange={(checked) => {
                        const enabled = checked as boolean;
                        setConfig(prev => ({
                          ...prev,
                          councilMode: enabled,
                          // Set sensible defaults when enabling, clear when disabling
                          councilModels: enabled ? DEFAULT_ADDITIONAL_MODELS : [],
                          councilChairmanModel: enabled ? DEFAULT_CHAIRMAN : ""
                        }));
                        setShowCouncilConfig(enabled);
                      }}
                    />
                    <Label htmlFor="council-mode" className="flex items-center gap-1.5 text-xs font-semibold cursor-pointer">
                      <Brain className="h-4 w-4 text-purple-400" />
                      Council Mode
                      <Badge variant="secondary" className="text-[9px] px-1.5 py-0 h-4 bg-purple-500/20 text-purple-400 border-purple-500/30">
                        EXPERIMENTAL
                      </Badge>
                    </Label>
                  </div>
                  {config.councilMode && (
                    <button
                      type="button"
                      onClick={() => setShowCouncilConfig(!showCouncilConfig)}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      {showCouncilConfig ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                  )}
                </div>

                <p className="text-[10px] text-muted-foreground leading-relaxed">
                  Your bot's AI model collaborates with additional models to reach consensus decisions through debate and voting.
                </p>

                {config.councilMode && showCouncilConfig && (
                  <div className="space-y-3 pt-2 border-t border-purple-500/20">
                    {/* Show Bot's Model as Lead */}
                    {selectedAgent && (
                      <div className="space-y-1">
                        <Label className="text-xs flex items-center gap-1.5">
                          <Bot className="h-3 w-3 text-purple-400" />
                          Lead Model (Your Bot)
                        </Label>
                        <Badge
                          variant="secondary"
                          className="text-[9px] px-2 py-1 bg-purple-500/20 text-purple-300 border-purple-500/30 font-semibold"
                        >
                          {selectedAgent.model.split('/')[1]?.split(':')[0] || selectedAgent.model}
                        </Badge>
                        <p className="text-[9px] text-muted-foreground">
                          Your bot's configured model leads the council
                        </p>
                      </div>
                    )}
                    
                    {/* Council Members Multi-Select */}
                    <div className="space-y-1.5">
                      <Label className="text-xs flex items-center gap-1.5">
                        <Brain className="h-3 w-3 text-blue-400" />
                        Additional Council Members ({config.councilModels.length}/3)
                      </Label>
                      
                      {/* Selected models as removable badges */}
                      {config.councilModels.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-1.5">
                          {config.councilModels.map((modelId) => {
                            const model = freeModels.find(m => m.id === modelId);
                            return (
                              <Badge
                                key={modelId}
                                variant="secondary"
                                className="text-[9px] px-2 py-0.5 bg-blue-500/10 text-blue-400 border-blue-500/20 flex items-center gap-1"
                              >
                                {model?.name.replace(' (Free)', '') || modelId.split('/')[1]?.split(':')[0] || modelId}
                                <button
                                  type="button"
                                  onClick={() => setConfig(prev => ({
                                    ...prev,
                                    councilModels: prev.councilModels.filter(m => m !== modelId)
                                  }))}
                                  className="hover:text-blue-200 ml-0.5"
                                >
                                  <X className="h-2.5 w-2.5" />
                                </button>
                              </Badge>
                            );
                          })}
                        </div>
                      )}
                      
                      {/* Dropdown to add models */}
                      {config.councilModels.length < 3 && (
                        <AnimatedSelect
                          value=""
                          onValueChange={(value) => {
                            if (value && !config.councilModels.includes(value)) {
                              setConfig(prev => ({
                                ...prev,
                                councilModels: [...prev.councilModels, value].slice(0, 3)
                              }));
                            }
                          }}
                        >
                          <AnimatedSelectTrigger className="h-7 text-[10px]">
                            <AnimatedSelectValue placeholder="+ Add council member..." />
                          </AnimatedSelectTrigger>
                          <AnimatedSelectContent>
                            {freeModels
                              .filter(m => !config.councilModels.includes(m.id) && m.id !== selectedAgent?.model)
                              .map((model) => (
                                <AnimatedSelectItem key={model.id} value={model.id} textValue={model.name}>
                                  <div className="flex items-center gap-2">
                                    <span className="text-[10px]">{model.name.replace(' (Free)', '')}</span>
                                    <span className="text-[9px] text-muted-foreground">{model.provider}</span>
                                  </div>
                                </AnimatedSelectItem>
                              ))}
                          </AnimatedSelectContent>
                        </AnimatedSelect>
                      )}
                      
                      <p className="text-[9px] text-muted-foreground">
                        {config.councilModels.length + 1} total models (including your bot) • Max 3 additional • Free-tier only
                      </p>
                    </div>
                    
                    {/* Chairman Select */}
                    <div className="space-y-1.5">
                      <Label className="text-xs flex items-center gap-1.5">
                        <Sparkles className="h-3 w-3 text-amber-400" />
                        Chairman (Final Synthesizer)
                      </Label>
                      <AnimatedSelect
                        value={config.councilChairmanModel}
                        onValueChange={(value) => setConfig(prev => ({ ...prev, councilChairmanModel: value }))}
                      >
                        <AnimatedSelectTrigger className="h-7 text-[10px]">
                          <AnimatedSelectValue placeholder="Select chairman model..." />
                        </AnimatedSelectTrigger>
                        <AnimatedSelectContent>
                          {freeModels.map((model) => (
                            <AnimatedSelectItem key={model.id} value={model.id} textValue={model.name}>
                              <div className="flex items-center gap-2">
                                <span className="text-[10px]">{model.name.replace(' (Free)', '')}</span>
                                {config.councilModels.includes(model.id) && (
                                  <Badge variant="outline" className="text-[8px] px-1 py-0 h-3">council</Badge>
                                )}
                                {model.id === selectedAgent?.model && (
                                  <Badge variant="outline" className="text-[8px] px-1 py-0 h-3 text-purple-400 border-purple-400/30">bot</Badge>
                                )}
                              </div>
                            </AnimatedSelectItem>
                          ))}
                        </AnimatedSelectContent>
                      </AnimatedSelect>
                      <p className="text-[9px] text-muted-foreground">
                        The chairman reviews all responses and synthesizes the final decision
                      </p>
                    </div>

                    <div className="flex items-start gap-1.5 rounded-md bg-amber-500/5 border border-amber-500/20 p-2 mt-2">
                      <Info className="h-3 w-3 text-amber-500 flex-shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        <p className="text-[9px] text-amber-600 dark:text-amber-400 leading-tight">
                          <strong>How it works:</strong> Your bot's model + {config.councilModels.length} additional models each analyze independently → 
                          rank each other's decisions → chairman synthesizes final verdict.
                        </p>
                        <p className="text-[9px] text-amber-600 dark:text-amber-400 leading-tight">
                          ⚠️ Takes 3-5x longer due to multiple LLM calls. Max 3 models recommended to avoid rate limits.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
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

