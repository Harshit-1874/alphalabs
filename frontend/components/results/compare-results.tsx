"use client";

import { useState, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  GitCompare,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  Clock,
  DollarSign,
  Check,
  X,
  Plus,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AnimatedSelect,
  AnimatedSelectContent,
  AnimatedSelectItem,
  AnimatedSelectTrigger,
  AnimatedSelectValue,
} from "@/components/ui/animated-select";
import { cn } from "@/lib/utils";
import { useResultsStore } from "@/lib/stores";
import { DUMMY_RESULTS } from "@/lib/dummy-data";
import type { TestResult } from "@/types/result";

interface ComparisonMetric {
  label: string;
  key: keyof TestResult | string;
  format: (value: number) => string;
  higherIsBetter: boolean;
  icon: React.ReactNode;
}

const metrics: ComparisonMetric[] = [
  {
    label: "PnL",
    key: "pnl",
    format: (v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`,
    higherIsBetter: true,
    icon: <TrendingUp className="h-4 w-4" />,
  },
  {
    label: "Win Rate",
    key: "winRate",
    format: (v) => `${v}%`,
    higherIsBetter: true,
    icon: <Target className="h-4 w-4" />,
  },
  {
    label: "Total Trades",
    key: "totalTrades",
    format: (v) => `${v}`,
    higherIsBetter: false, // Neutral
    icon: <Activity className="h-4 w-4" />,
  },
  {
    label: "Max Drawdown",
    key: "maxDrawdown",
    format: (v) => `${v}%`,
    higherIsBetter: false, // Lower is better (less negative)
    icon: <TrendingDown className="h-4 w-4" />,
  },
  {
    label: "Sharpe Ratio",
    key: "sharpeRatio",
    format: (v) => v.toFixed(2),
    higherIsBetter: true,
    icon: <Activity className="h-4 w-4" />,
  },
  {
    label: "Profit Factor",
    key: "profitFactor",
    format: (v) => v.toFixed(2),
    higherIsBetter: true,
    icon: <DollarSign className="h-4 w-4" />,
  },
];

export function CompareResults() {
  const searchParams = useSearchParams();
  const { results: storeResults } = useResultsStore();
  const results = storeResults.length > 0 ? storeResults : DUMMY_RESULTS;

  // Get initial selections from URL params
  const initialLeft = searchParams.get("left") || "";
  const initialRight = searchParams.get("right") || "";

  const [leftResultId, setLeftResultId] = useState<string>(initialLeft);
  const [rightResultId, setRightResultId] = useState<string>(initialRight);

  const leftResult = results.find((r) => r.id === leftResultId);
  const rightResult = results.find((r) => r.id === rightResultId);

  const getWinner = (metric: ComparisonMetric): "left" | "right" | "tie" | null => {
    if (!leftResult || !rightResult) return null;
    
    const leftValue = leftResult[metric.key as keyof TestResult] as number;
    const rightValue = rightResult[metric.key as keyof TestResult] as number;

    if (leftValue === rightValue) return "tie";
    
    if (metric.key === "maxDrawdown") {
      // For drawdown, closer to 0 is better (less negative)
      return leftValue > rightValue ? "left" : "right";
    }
    
    if (metric.higherIsBetter) {
      return leftValue > rightValue ? "left" : "right";
    } else {
      return leftValue < rightValue ? "left" : "right";
    }
  };

  const overallScore = useMemo(() => {
    if (!leftResult || !rightResult) return { left: 0, right: 0 };
    
    let leftWins = 0;
    let rightWins = 0;
    
    metrics.forEach((metric) => {
      const winner = getWinner(metric);
      if (winner === "left") leftWins++;
      if (winner === "right") rightWins++;
    });
    
    return { left: leftWins, right: rightWins };
  }, [leftResult, rightResult]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/dashboard/results"
          className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Results
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[hsl(var(--brand-flame)/0.2)]">
            <GitCompare className="h-5 w-5 text-[hsl(var(--brand-flame))]" />
          </div>
          <div>
            <h1 className="font-mono text-2xl font-bold">Compare Results</h1>
            <p className="text-sm text-muted-foreground">
              Side-by-side performance comparison
            </p>
          </div>
        </div>
      </div>

      {/* Selection Row */}
      <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr]">
        {/* Left Selection */}
        <Card className="border-border/50 bg-card/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Result A
            </CardTitle>
          </CardHeader>
          <CardContent>
            <AnimatedSelect value={leftResultId} onValueChange={setLeftResultId}>
              <AnimatedSelectTrigger>
                <AnimatedSelectValue placeholder="Select a result..." />
              </AnimatedSelectTrigger>
              <AnimatedSelectContent>
                {results.map((result) => (
                  <AnimatedSelectItem 
                    key={result.id} 
                    value={result.id}
                    textValue={result.agentName}
                    disabled={result.id === rightResultId}
                  >
                    <span className="font-mono">{result.agentName}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {result.pnl >= 0 ? "+" : ""}{result.pnl.toFixed(1)}%
                    </span>
                  </AnimatedSelectItem>
                ))}
              </AnimatedSelectContent>
            </AnimatedSelect>
            {leftResult && (
              <div className="mt-3 flex items-center justify-between">
                <Badge variant="outline">{leftResult.type}</Badge>
                <span className={cn(
                  "font-mono text-lg font-bold",
                  leftResult.pnl >= 0 ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
                )}>
                  {leftResult.pnl >= 0 ? "+" : ""}{leftResult.pnl.toFixed(2)}%
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* VS Badge */}
        <div className="flex items-center justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-border bg-card">
            <span className="font-mono text-sm font-bold text-muted-foreground">VS</span>
          </div>
        </div>

        {/* Right Selection */}
        <Card className="border-border/50 bg-card/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Result B
            </CardTitle>
          </CardHeader>
          <CardContent>
            <AnimatedSelect value={rightResultId} onValueChange={setRightResultId}>
              <AnimatedSelectTrigger>
                <AnimatedSelectValue placeholder="Select a result..." />
              </AnimatedSelectTrigger>
              <AnimatedSelectContent>
                {results.map((result) => (
                  <AnimatedSelectItem 
                    key={result.id} 
                    value={result.id}
                    textValue={result.agentName}
                    disabled={result.id === leftResultId}
                  >
                    <span className="font-mono">{result.agentName}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {result.pnl >= 0 ? "+" : ""}{result.pnl.toFixed(1)}%
                    </span>
                  </AnimatedSelectItem>
                ))}
              </AnimatedSelectContent>
            </AnimatedSelect>
            {rightResult && (
              <div className="mt-3 flex items-center justify-between">
                <Badge variant="outline">{rightResult.type}</Badge>
                <span className={cn(
                  "font-mono text-lg font-bold",
                  rightResult.pnl >= 0 ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
                )}>
                  {rightResult.pnl >= 0 ? "+" : ""}{rightResult.pnl.toFixed(2)}%
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Comparison Table */}
      {leftResult && rightResult ? (
        <Card className="border-border/50 bg-card/30 overflow-hidden">
          {/* Score Header */}
          <div className="grid grid-cols-[1fr_auto_1fr] border-b border-border/50">
            <div className={cn(
              "p-4 text-center",
              overallScore.left > overallScore.right && "bg-[hsl(var(--accent-green)/0.1)]"
            )}>
              <p className="text-xs text-muted-foreground">WINS</p>
              <p className="font-mono text-2xl font-bold">{overallScore.left}</p>
            </div>
            <div className="flex items-center justify-center border-x border-border/50 px-6">
              <span className="text-xs text-muted-foreground">SCORE</span>
            </div>
            <div className={cn(
              "p-4 text-center",
              overallScore.right > overallScore.left && "bg-[hsl(var(--accent-green)/0.1)]"
            )}>
              <p className="text-xs text-muted-foreground">WINS</p>
              <p className="font-mono text-2xl font-bold">{overallScore.right}</p>
            </div>
          </div>

          {/* Metrics Comparison */}
          <div className="divide-y divide-border/50">
            {metrics.map((metric) => {
              const winner = getWinner(metric);
              const leftValue = leftResult[metric.key as keyof TestResult] as number;
              const rightValue = rightResult[metric.key as keyof TestResult] as number;

              return (
                <div key={metric.key} className="grid grid-cols-[1fr_auto_1fr]">
                  {/* Left Value */}
                  <div className={cn(
                    "flex items-center justify-between p-4",
                    winner === "left" && "bg-[hsl(var(--accent-green)/0.05)]"
                  )}>
                    <span className={cn(
                      "font-mono text-lg",
                      winner === "left" && "text-[hsl(var(--accent-green))] font-bold"
                    )}>
                      {metric.format(leftValue)}
                    </span>
                    {winner === "left" && (
                      <Check className="h-5 w-5 text-[hsl(var(--accent-green))]" />
                    )}
                  </div>

                  {/* Metric Label */}
                  <div className="flex items-center justify-center gap-2 border-x border-border/50 px-4 bg-muted/20">
                    {metric.icon}
                    <span className="text-sm font-medium">{metric.label}</span>
                  </div>

                  {/* Right Value */}
                  <div className={cn(
                    "flex items-center justify-between p-4",
                    winner === "right" && "bg-[hsl(var(--accent-green)/0.05)]"
                  )}>
                    {winner === "right" && (
                      <Check className="h-5 w-5 text-[hsl(var(--accent-green))]" />
                    )}
                    <span className={cn(
                      "font-mono text-lg ml-auto",
                      winner === "right" && "text-[hsl(var(--accent-green))] font-bold"
                    )}>
                      {metric.format(rightValue)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      ) : (
        <Card className="border-border/50 bg-card/30">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <GitCompare className="mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="font-mono text-lg font-medium">Select Two Results</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Choose two test results above to compare their performance metrics
            </p>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      {leftResult && rightResult && (
        <div className="flex justify-center gap-3">
          <Button asChild variant="outline">
            <Link href={`/dashboard/results/${leftResultId}`}>
              View {leftResult.agentName} Details
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href={`/dashboard/results/${rightResultId}`}>
              View {rightResult.agentName} Details
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}

