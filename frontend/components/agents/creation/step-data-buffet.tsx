"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { cn } from "@/lib/utils";
import type { StepDataBuffetProps, AgentMode } from "@/types/agent";

// Shadcn-style chart colors for variety
const badgeColors = [
  "bg-[hsl(var(--chart-1))]/15 text-[hsl(var(--chart-1))] border-[hsl(var(--chart-1))]/30",
  "bg-[hsl(var(--chart-2))]/15 text-[hsl(var(--chart-2))] border-[hsl(var(--chart-2))]/30",
  "bg-[hsl(var(--chart-3))]/15 text-[hsl(var(--chart-3))] border-[hsl(var(--chart-3))]/30",
  "bg-[hsl(var(--chart-4))]/15 text-[hsl(var(--chart-4))] border-[hsl(var(--chart-4))]/30",
  "bg-[hsl(var(--chart-5))]/15 text-[hsl(var(--chart-5))] border-[hsl(var(--chart-5))]/30",
];

// Indicators available in the Buffet
const indicatorCategories = [
  {
    id: "momentum",
    name: "Momentum",
    indicators: [
      { id: "rsi", name: "RSI", description: "Relative Strength Index - Measures overbought/oversold conditions" },
      { id: "stochastic", name: "Stochastic", description: "Momentum indicator comparing close to price range" },
      { id: "cci", name: "CCI", description: "Commodity Channel Index - Identifies cyclical trends" },
      { id: "mom", name: "MOM", description: "Momentum - Rate of price change" },
      { id: "ao", name: "AO", description: "Awesome Oscillator - Market momentum measurement" },
    ],
  },
  {
    id: "trend",
    name: "Trend",
    indicators: [
      { id: "macd", name: "MACD", description: "Moving Average Convergence Divergence" },
      { id: "ema", name: "EMA", description: "Exponential Moving Average (20/50/200)" },
      { id: "sma", name: "SMA", description: "Simple Moving Average" },
      { id: "adx", name: "ADX", description: "Average Directional Index" },
      { id: "psar", name: "Parabolic SAR", description: "Stop and Reverse indicator" },
      { id: "ichimoku", name: "Ichimoku Cloud", description: "Complete trend system" },
    ],
  },
  {
    id: "volatility",
    name: "Volatility",
    indicators: [
      { id: "atr", name: "ATR", description: "Average True Range - Volatility measurement" },
      { id: "bb", name: "Bollinger Bands", description: "Volatility bands around SMA" },
      { id: "keltner", name: "Keltner Channels", description: "Volatility-based envelope" },
      { id: "dc", name: "Donchian Channels", description: "Price channel breakout" },
    ],
  },
  {
    id: "volume",
    name: "Volume",
    indicators: [
      { id: "obv", name: "OBV", description: "On Balance Volume - Volume flow" },
      { id: "vwap", name: "VWAP", description: "Volume Weighted Average Price" },
      { id: "mfi", name: "MFI", description: "Money Flow Index - Volume-weighted RSI" },
      { id: "cmf", name: "CMF", description: "Chaikin Money Flow - Volume-weighted price trend" },
      { id: "ad", name: "A/D Line", description: "Accumulation/Distribution" },
    ],
  },
  {
    id: "advanced",
    name: "Advanced",
    indicators: [
      { id: "supertrend", name: "Supertrend", description: "Trend-following indicator using ATR" },
      { id: "zscore", name: "Z-Score", description: "Statistical mean reversion indicator" },
    ],
  },
];

// Monk Mode is intentionally information-deprived: only RSI and MACD
const MONK_ALLOWED_INDICATORS: string[] = ["rsi", "macd"];

// Preset indicator selections
const presets = {
  monkEssentials: MONK_ALLOWED_INDICATORS,
  all: indicatorCategories.flatMap((cat) => cat.indicators.map((ind) => ind.id)),
};

export function StepDataBuffet({ formData, updateFormData }: StepDataBuffetProps) {
  const [activeTab, setActiveTab] = useState("indicators");

  // When switching to Monk mode, automatically drop any unsupported indicators
  useEffect(() => {
    if (formData.mode === "monk") {
      const filtered = formData.indicators.filter((id) =>
        MONK_ALLOWED_INDICATORS.includes(id)
      );
      if (filtered.length !== formData.indicators.length) {
        updateFormData({ indicators: filtered });
      }
    }
  }, [formData.mode, formData.indicators, updateFormData]);

  const toggleIndicator = (indicatorId: string) => {
    // In Monk mode we only allow RSI and MACD. Ignore toggles for others.
    if (formData.mode === "monk" && !MONK_ALLOWED_INDICATORS.includes(indicatorId)) {
      return;
    }

    const newIndicators = formData.indicators.includes(indicatorId)
      ? formData.indicators.filter((id) => id !== indicatorId)
      : [...formData.indicators, indicatorId];
    updateFormData({ indicators: newIndicators });
  };

  const applyPreset = (preset: keyof typeof presets) => {
    updateFormData({ indicators: presets[preset] });
  };

  const clearAll = () => {
    updateFormData({ indicators: [] });
  };

  const getSelectedCount = (categoryId: string) => {
    const category = indicatorCategories.find((c) => c.id === categoryId);
    if (!category) return 0;
    return category.indicators.filter((ind) =>
      formData.indicators.includes(ind.id)
    ).length;
  };

  return (
    <div className="space-y-6">
      {/* Description */}
      <p className="text-sm text-muted-foreground">
        Select the data your agent will receive. The AI doesn&apos;t do math - we
        calculate all indicators and feed them as text.
      </p>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="price">Price Data</TabsTrigger>
          <TabsTrigger value="indicators">Indicators</TabsTrigger>
          <TabsTrigger value="custom">Custom</TabsTrigger>
        </TabsList>

        {/* Price Data Tab */}
        <TabsContent value="price" className="mt-4">
          <div className="rounded-lg border border-border/50 bg-muted/20 p-4">
            <p className="mb-3 text-sm font-medium">Always Included:</p>
            <div className="flex flex-wrap gap-2">
              {["Open", "High", "Low", "Close", "Volume", "Timestamp"].map(
                (item) => (
                  <Badge key={item} variant="outline">
                    {item}
                  </Badge>
                )
              )}
            </div>
          </div>
        </TabsContent>

        {/* Indicators Tab */}
        <TabsContent value="indicators" className="mt-4 space-y-4">
          {/* Quick Select */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyPreset("all")}
            >
              Select All
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyPreset("monkEssentials")}
            >
              Monk Essentials
            </Button>
            <Button variant="outline" size="sm" onClick={clearAll}>
              Clear All
            </Button>
          </div>

          {/* Indicator Categories Accordion */}
          <Accordion type="multiple" className="w-full space-y-2">
            {indicatorCategories.map((category) => {
              const selectedCount = getSelectedCount(category.id);
              const totalCount = category.indicators.length;

              return (
                <AccordionItem
                  key={category.id}
                  value={category.id}
                  className="rounded-lg border border-border/50 bg-muted/10 px-4"
                >
                  <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center gap-3">
                      <span className="font-medium">{category.name}</span>
                      <Badge
                        variant="secondary"
                        className={cn(
                          selectedCount > 0 &&
                            "bg-primary/20 text-primary"
                        )}
                      >
                        {selectedCount}/{totalCount}
                      </Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-3 pb-2">
                      {category.indicators.map((indicator) => (
                        <div
                          key={indicator.id}
                          className="flex items-start gap-3"
                        >
                          <Checkbox
                            id={indicator.id}
                            checked={formData.indicators.includes(indicator.id)}
                            disabled={
                              formData.mode === "monk" &&
                              !MONK_ALLOWED_INDICATORS.includes(indicator.id)
                            }
                            onCheckedChange={() => toggleIndicator(indicator.id)}
                          />
                          <div className="flex-1">
                            <label
                              htmlFor={indicator.id}
                              className="text-sm font-medium cursor-pointer"
                            >
                              {indicator.name}
                            </label>
                            <p className="text-xs text-muted-foreground">
                              {indicator.description}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>

          {/* Selected Summary - horizontally scrollable */}
          {formData.indicators.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                SELECTED INDICATORS ({formData.indicators.length})
              </p>
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
                {formData.indicators.map((id, index) => {
                  const indicator = indicatorCategories
                    .flatMap((c) => c.indicators)
                    .find((i) => i.id === id);
                  const colorClass = badgeColors[index % badgeColors.length];
                  return (
                    <Badge
                      key={id}
                      variant="outline"
                      className={cn("shrink-0 gap-1 pr-1", colorClass)}
                    >
                      {indicator?.name || id}
                      <button
                        onClick={() => toggleIndicator(id)}
                        className="ml-1 rounded-full p-0.5 hover:bg-black/10 dark:hover:bg-white/10"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  );
                })}
              </div>
            </div>
          )}
        </TabsContent>

        {/* Custom Tab */}
        <TabsContent value="custom" className="mt-4">
          <div className="rounded-lg border border-border/50 bg-muted/20 p-6 text-center">
            <p className="text-sm text-muted-foreground">
              Custom indicator builder coming soon!
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Create formulas using price data and standard indicators.
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

