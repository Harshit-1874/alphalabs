"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ChevronLeft,
  Download,
  Share2,
  Award,
  TrendingUp,
  TrendingDown,
  Target,
  Scale,
  Calendar,
  Clock,
  BarChart3,
  ListOrdered,
} from "lucide-react";
import { Robot, Lightning } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { EquityCurveChart } from "@/components/charts/equity-curve-chart";
import {
  DUMMY_RESULTS,
  DUMMY_TRADES,
  DUMMY_AI_THOUGHTS,
  generateDummyEquityCurve,
} from "@/lib/dummy-data";

interface ResultDetailProps {
  resultId: string;
}

export function ResultDetail({ resultId }: ResultDetailProps) {
  const [tab, setTab] = useState("equity");
  
  // Find result or use first one as demo
  const result = DUMMY_RESULTS.find((r) => r.id === resultId) || DUMMY_RESULTS[0];
  const isProfitable = result.pnl >= 0;
  const equityCurve = generateDummyEquityCurve(200);
  const trades = DUMMY_TRADES;
  const thoughts = DUMMY_AI_THOUGHTS;

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

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <Badge
                variant={result.type === "forward" ? "default" : "secondary"}
                className="text-xs"
              >
                {result.type === "forward" ? "FORWARD TEST" : "BACKTEST"} #{result.id}
              </Badge>
              <span
                className={cn(
                  "font-mono text-2xl font-bold",
                  isProfitable
                    ? "text-[hsl(var(--accent-green))]"
                    : "text-[hsl(var(--accent-red))]"
                )}
              >
                {isProfitable ? "+" : ""}
                {result.pnl}%
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              <span className="font-mono font-medium">{result.agentName}</span>
              {" • "}
              {result.asset}
              {" • "}
              <span className="capitalize">{result.mode} Mode</span>
            </p>
            <p className="text-xs text-muted-foreground">
              {result.date.toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
              {" • "}
              {result.duration}
            </p>
          </div>

          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-2">
              <Download className="h-4 w-4" />
              Export
            </Button>
            {isProfitable && (
              <>
                <Button variant="outline" size="sm" className="gap-2">
                  <Share2 className="h-4 w-4" />
                  Share
                </Button>
                <Button
                  size="sm"
                  className="gap-2 bg-[hsl(var(--brand-flame))] text-white hover:bg-[hsl(var(--brand-flame))]/90"
                >
                  <Award className="h-4 w-4" />
                  Certificate
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Scorecard */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/50 bg-card/30">
          <CardContent className="flex items-center gap-3 p-4">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg",
                isProfitable
                  ? "bg-[hsl(var(--accent-green)/0.1)]"
                  : "bg-[hsl(var(--accent-red)/0.1)]"
              )}
            >
              {isProfitable ? (
                <TrendingUp className="h-5 w-5 text-[hsl(var(--accent-green))]" />
              ) : (
                <TrendingDown className="h-5 w-5 text-[hsl(var(--accent-red))]" />
              )}
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total PnL</p>
              <p
                className={cn(
                  "font-mono text-xl font-bold",
                  isProfitable
                    ? "text-[hsl(var(--accent-green))]"
                    : "text-[hsl(var(--accent-red))]"
                )}
              >
                {isProfitable ? "+" : ""}
                {result.pnl}%
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/30">
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted/50">
              <Target className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Win Rate</p>
              <p className="font-mono text-xl font-bold">{result.winRate}%</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/30">
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[hsl(var(--accent-red)/0.1)]">
              <Scale className="h-5 w-5 text-[hsl(var(--accent-red))]" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Max Drawdown</p>
              <p className="font-mono text-xl font-bold text-[hsl(var(--accent-red))]">
                {result.maxDrawdown}%
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/30">
          <CardContent className="flex items-center gap-3 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted/50">
              <BarChart3 className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total Trades</p>
              <p className="font-mono text-xl font-bold">{result.trades}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Additional Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Sharpe Ratio</span>
              <span className="font-mono font-medium">{result.sharpeRatio || "1.8"}</span>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Profit Factor</span>
              <span className="font-mono font-medium">{result.profitFactor || "2.1"}</span>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Avg Trade</span>
              <span className="font-mono font-medium">+0.52%</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="equity" className="gap-2">
            <TrendingUp className="h-4 w-4" />
            Equity Curve
          </TabsTrigger>
          <TabsTrigger value="trades" className="gap-2">
            <ListOrdered className="h-4 w-4" />
            Trade List
          </TabsTrigger>
          <TabsTrigger value="reasoning" className="gap-2">
            <Robot size={16} weight="duotone" />
            Reasoning
          </TabsTrigger>
          <TabsTrigger value="analysis" className="gap-2">
            <Lightning size={16} weight="duotone" />
            AI Analysis
          </TabsTrigger>
        </TabsList>

        <TabsContent value="equity" className="mt-6">
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="text-base">Equity Curve</CardTitle>
            </CardHeader>
            <CardContent>
              <EquityCurveChart data={equityCurve} height={350} showDrawdown />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trades" className="mt-6">
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="text-base">Trade History</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Entry</TableHead>
                    <TableHead>Exit</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead className="text-right">PnL</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trades.map((trade, index) => (
                    <TableRow key={trade.id}>
                      <TableCell className="font-mono">{index + 1}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn(
                            trade.type === "long"
                              ? "border-[hsl(var(--accent-green)/0.3)] text-[hsl(var(--accent-green))]"
                              : "border-[hsl(var(--accent-red)/0.3)] text-[hsl(var(--accent-red))]"
                          )}
                        >
                          {trade.type.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono">
                        ${trade.entryPrice.toLocaleString()}
                      </TableCell>
                      <TableCell className="font-mono">
                        ${trade.exitPrice.toLocaleString()}
                      </TableCell>
                      <TableCell className="font-mono">{trade.size}</TableCell>
                      <TableCell
                        className={cn(
                          "text-right font-mono font-medium",
                          trade.pnl >= 0
                            ? "text-[hsl(var(--accent-green))]"
                            : "text-[hsl(var(--accent-red))]"
                        )}
                      >
                        {trade.pnl >= 0 ? "+" : ""}
                        {trade.pnlPercent}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reasoning" className="mt-6">
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="text-base">AI Reasoning Trace</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                  {thoughts.map((thought) => (
                    <div
                      key={thought.id}
                      className="rounded-lg border border-border/50 bg-muted/20 p-4"
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <Badge variant="outline" className="text-xs">
                          {thought.type}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Candle #{thought.candle}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">{thought.content}</p>
                      {thought.action && (
                        <div className="mt-2">
                          <Badge
                            className={cn(
                              thought.action === "long" &&
                                "bg-[hsl(var(--accent-green))] text-black",
                              thought.action === "short" &&
                                "bg-[hsl(var(--accent-red))] text-white"
                            )}
                          >
                            Action: {thought.action.toUpperCase()}
                          </Badge>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="mt-6">
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Lightning size={18} weight="duotone" className="text-[hsl(var(--brand-flame))]" />
                AI Performance Analysis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 text-sm text-muted-foreground">
                <p>
                  <strong className="text-foreground">Overall Assessment:</strong>{" "}
                  The agent demonstrated {isProfitable ? "strong" : "inconsistent"} performance
                  over the test period with a {result.winRate}% win rate.
                </p>
                <p>
                  <strong className="text-foreground">Strengths:</strong>{" "}
                  {isProfitable
                    ? "Effective trend identification, disciplined risk management, and consistent entry timing."
                    : "The strategy showed promise in certain market conditions but struggled with volatility."}
                </p>
                <p>
                  <strong className="text-foreground">Areas for Improvement:</strong>{" "}
                  Consider refining exit timing to capture more profit on winning trades.
                  The drawdown of {result.maxDrawdown}% suggests position sizing could be optimized.
                </p>
                <p>
                  <strong className="text-foreground">Market Conditions:</strong>{" "}
                  The test period included various market regimes including trending and ranging phases.
                  {isProfitable
                    ? " The strategy adapted well to changing conditions."
                    : " Better performance observed during trending markets."}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

