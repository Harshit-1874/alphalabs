"use client";

import { useCallback, useEffect, useState } from "react";
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
import { useResultsApi } from "@/hooks/use-results-api";
import { useCertificateApi } from "@/hooks/use-certificate-api";
import { toast } from "sonner";
import type { EquityCurvePoint } from "@/types";
import type {
  ReasoningEntry,
  ResultDetailResponse,
  ResultTrade,
} from "@/types/result";

interface ResultDetailProps {
  resultId: string;
}

const normalizeEquityCurve = (curve?: Array<Record<string, unknown>>): EquityCurvePoint[] => {
  if (!curve) return [];

  const normalized: EquityCurvePoint[] = [];

  for (const point of curve) {
    const rawTime = point.time ?? point.timestamp;
    const timestamp =
      typeof rawTime === "number"
        ? rawTime
        : typeof rawTime === "string"
        ? new Date(rawTime).getTime()
        : undefined;

    if (!timestamp) {
      continue;
    }

    normalized.push({
      time: timestamp,
      value: Number(point.value ?? point.equity ?? 0),
      drawdown: Number(point.drawdown ?? 0),
    });
  }

  return normalized;
};

const formatDurationLabel = (start?: string, end?: string) => {
  if (!start) return "–";
  const startDate = new Date(start);
  const endDate = end ? new Date(end) : new Date();
  const diffMs = endDate.getTime() - startDate.getTime();
  if (diffMs <= 0) return "0s";
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (days >= 1) return `${days}d`;
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  if (hours >= 1) return `${hours}h`;
  const minutes = Math.floor(diffMs / (1000 * 60));
  return `${minutes}m`;
};

export function ResultDetail({ resultId }: ResultDetailProps) {
  const [tab, setTab] = useState("equity");
  const { fetchResultDetail, fetchTrades, fetchReasoning } = useResultsApi();
  const { createCertificate, downloadCertificatePdf } = useCertificateApi();
  const [result, setResult] = useState<ResultDetailResponse["result"] | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityCurvePoint[]>([]);
  const [trades, setTrades] = useState<ResultTrade[]>([]);
  const [thoughts, setThoughts] = useState<ReasoningEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreatingCertificate, setIsCreatingCertificate] = useState(false);
  const [certificate, setCertificate] = useState<{ share_url: string; id: string } | null>(null);

  const loadResult = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [detailResponse, tradesResponse, reasoningResponse] = await Promise.all([
        fetchResultDetail(resultId),
        fetchTrades(resultId, { limit: 100 }),
        fetchReasoning(resultId, { limit: 100 }),
      ]);
      setResult(detailResponse.result);
      setEquityCurve(normalizeEquityCurve(detailResponse.result.equity_curve ?? []));
      setTrades(tradesResponse.trades);
      setThoughts(reasoningResponse.thoughts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load result");
    } finally {
      setIsLoading(false);
    }
  }, [fetchResultDetail, fetchTrades, fetchReasoning, resultId]);

  useEffect(() => {
    void loadResult();
  }, [loadResult]);

  const handleCreateCertificate = useCallback(async () => {
    if (!result) return;
    
    const totalPnL = result.total_pnl_pct ?? 0;
    const isProfitable = totalPnL >= 0;
    if (!isProfitable) return;
    
    setIsCreatingCertificate(true);
    try {
      const cert = await createCertificate(result.id);
      setCertificate(cert);
      toast.success("Certificate created successfully!");
      // Open certificate PDF
      downloadCertificatePdf(cert.id);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to create certificate";
      toast.error(errorMessage);
      console.error("Certificate creation error:", err);
    } finally {
      setIsCreatingCertificate(false);
    }
  }, [result, createCertificate, downloadCertificatePdf]);

  const handleShare = useCallback(async () => {
    if (!result) return;

    const totalPnL = result.total_pnl_pct ?? 0;
    const isProfitable = totalPnL >= 0;
    if (!isProfitable) return;

    // If certificate exists, share it; otherwise create one first
    let shareUrl: string;
    
    if (certificate) {
      shareUrl = certificate.share_url;
    } else {
      try {
        setIsCreatingCertificate(true);
        const cert = await createCertificate(result.id);
        setCertificate(cert);
        shareUrl = cert.share_url;
      } catch (err) {
        toast.error("Failed to create certificate for sharing");
        console.error("Certificate creation error:", err);
        return;
      } finally {
        setIsCreatingCertificate(false);
      }
    }

    const shareData = {
      title: `AlphaLab Certificate - ${result.agent_name}`,
      text: `My AI trading agent "${result.agent_name}" achieved ${isProfitable ? "+" : ""}${(totalPnL ?? 0).toFixed(2)}% return on AlphaLab! 🚀`,
      url: shareUrl,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
        toast.success("Shared successfully!");
      } catch (err) {
        // User cancelled or share failed, fall back to clipboard
        await navigator.clipboard.writeText(shareUrl);
        toast.success("Certificate link copied to clipboard!");
      }
    } else {
      // Fallback to clipboard
      await navigator.clipboard.writeText(shareUrl);
      toast.success("Certificate link copied to clipboard!");
    }
  }, [result, certificate, createCertificate]);

  const handleExport = useCallback(() => {
    // TODO: Implement export functionality
    toast.info("Export functionality coming soon!");
  }, []);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/30 p-6 text-sm text-muted-foreground">
        Loading result details...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/50 bg-destructive/10 p-6 text-sm text-destructive">
        {error}
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/30 p-6 text-sm text-muted-foreground">
        Result not found.
      </div>
    );
  }

  const totalPnL = result.total_pnl_pct ?? 0;
  const isProfitable = totalPnL >= 0;
  const winRate = result.win_rate ?? 0;
  const maxDrawdown = result.max_drawdown_pct ?? 0;
  const totalTrades = result.total_trades ?? 0;
  const createdAt = result.start_date ? new Date(result.start_date) : new Date();
  const durationDisplay = formatDurationLabel(
    result.start_date ?? undefined,
    result.end_date ?? undefined
  );
  const analysisText =
    result.ai_summary ??
    `Overall performance derived from ${totalTrades} trades with ${(winRate ?? 0).toFixed(1)}% win rate.`;
  const avgTrade = result.avg_trade_pnl != null ? `${(result.avg_trade_pnl ?? 0).toFixed(2)}%` : "—";

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
              {(totalPnL ?? 0).toFixed(2)}%
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              <span className="font-mono font-medium">{result.agent_name}</span>
              {" • "}
              {result.asset}
              {" • "}
              <span className="capitalize">{result.mode} Mode</span>
            </p>
            <p className="text-xs text-muted-foreground">
              {createdAt.toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
              {" • "}
              {durationDisplay}
            </p>
          </div>

          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              className="gap-2"
              onClick={handleExport}
            >
              <Download className="h-4 w-4" />
              Export
            </Button>
            {isProfitable && (
              <Button
                size="sm"
                className="gap-2 bg-[hsl(var(--brand-flame))] text-white hover:bg-[hsl(var(--brand-flame))]/90"
                onClick={handleShare}
                disabled={isCreatingCertificate}
              >
                <Share2 className="h-4 w-4" />
                {isCreatingCertificate ? "Creating..." : "Share Certificate"}
              </Button>
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
                {(totalPnL ?? 0).toFixed(2)}%
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
              <p className="font-mono text-xl font-bold">{(winRate ?? 0).toFixed(1)}%</p>
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
                {(maxDrawdown ?? 0).toFixed(2)}%
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
              <p className="font-mono text-xl font-bold">{totalTrades}</p>
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
              <span className="font-mono font-medium">{(result.sharpe_ratio ?? 0).toFixed(2)}</span>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Profit Factor</span>
              <span className="font-mono font-medium">{(result.profit_factor ?? 0).toFixed(2)}</span>
            </div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Avg Trade</span>
              <span className="font-mono font-medium">{avgTrade}</span>
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
              {trades.length === 0 ? (
                <div className="rounded-md border border-border/50 bg-muted/20 p-6 text-center text-sm text-muted-foreground">
                  No trades recorded for this result yet.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Entry</TableHead>
                      <TableHead>Exit</TableHead>
                      <TableHead>Notes</TableHead>
                      <TableHead className="text-right">PnL</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trades.map((trade, index) => (
                      <TableRow key={`${trade.trade_number}-${index}`}>
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
                          ${trade.entry_price?.toLocaleString() ?? "—"}
                        </TableCell>
                        <TableCell className="font-mono">
                          ${trade.exit_price?.toLocaleString() ?? "—"}
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {trade.entry_reasoning ?? trade.exit_reasoning ?? "–"}
                        </TableCell>
                        <TableCell
                          className={cn(
                            "text-right font-mono font-medium",
                            (trade.pnl_pct ?? 0) >= 0
                              ? "text-[hsl(var(--accent-green))]"
                              : "text-[hsl(var(--accent-red))]"
                          )}
                        >
                          {(trade.pnl_pct ?? 0) >= 0 ? "+" : ""}
                          {(trade.pnl_pct ?? 0).toFixed(2)}%
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
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
                {thoughts.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                    No AI reasoning available for this result.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {thoughts.map((thought) => (
                      <div
                        key={`${thought.candle_number}-${thought.timestamp}`}
                        className="rounded-lg border border-border/50 bg-muted/20 p-4"
                      >
                        <div className="mb-2 flex items-center justify-between">
                        <Badge variant="outline" className="text-xs capitalize">
                          {thought.decision ?? "analysis"}
                        </Badge>
                          <span className="text-xs text-muted-foreground">
                            Candle #{thought.candle_number}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">{thought.reasoning}</p>
                        {thought.decision && (
                          <div className="mt-2">
                            <Badge className="bg-[hsl(var(--accent-green)/0.2)] text-[hsl(var(--accent-green))]">
                              Decision: {thought.decision.toUpperCase()}
                            </Badge>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
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
                  {analysisText}
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
                  The drawdown of {(maxDrawdown ?? 0).toFixed(2)}% suggests position sizing could be optimized.
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

