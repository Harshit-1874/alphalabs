"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart3, Search, FileText, Share2, ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  AnimatedSelect,
  AnimatedSelectContent,
  AnimatedSelectItem,
  AnimatedSelectTrigger,
  AnimatedSelectValue,
} from "@/components/ui/animated-select";
import { cn } from "@/lib/utils";
import { useResultsApi, type ResultListParams } from "@/hooks/use-results-api";
import { useResultsStore } from "@/lib/stores/results-store";
import type { ResultListItem, ResultFilters, ResultPagination, ResultsStats } from "@/types/result";

interface ResultCardProps {
  result: ResultListItem;
}

function ResultCard({ result }: ResultCardProps) {
  const isProfitable = result.isProfitable ?? result.totalPnlPct >= 0;
  const createdAt = useMemo(() => new Date(result.createdAt), [result.createdAt]);
  const durationDisplay = result.durationDisplay ?? "—";

  return (
    <Card className="group border-border/50 bg-card/30 transition-colors hover:bg-muted/20">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-start gap-3 sm:gap-4">
          {/* Status Indicator */}
          <div
            className={cn(
              "mt-1.5 h-2 w-2 shrink-0 rounded-full",
              isProfitable ? "bg-[hsl(var(--accent-green))]" : "bg-[hsl(var(--accent-red))]"
            )}
          />

          {/* Content */}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={result.type === "forward" ? "default" : "secondary"} className="text-[10px] sm:text-xs">
                {result.type === "forward" ? "FORWARD" : "BACKTEST"} #{result.id}
              </Badge>
              <span
                className={cn(
                  "ml-auto font-mono text-base sm:text-lg font-bold",
                  isProfitable ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
                )}
              >
                {isProfitable ? "+" : ""}
                {result.totalPnlPct.toFixed(2)}%
              </span>
            </div>

            <div className="mt-2">
              <p className="text-sm">
                <span className="font-mono font-medium">{result.agentName}</span>
                <span className="text-muted-foreground"> • {result.asset}</span>
                <span className="hidden sm:inline text-muted-foreground"> • </span>
                <span className="hidden sm:inline capitalize text-muted-foreground">{result.mode} Mode</span>
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {createdAt.toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })}
                {" • "}
                {durationDisplay}
                {" • "}
                {result.totalTrades} trades
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Win: {result.winRate?.toFixed(1) ?? "—"}% • DD: {result.maxDrawdownPct?.toFixed(2) ?? "—"}%
              </p>
            </div>

            {/* Actions */}
            <div className="mt-3 flex flex-wrap items-center gap-1 sm:gap-2 border-t border-border/50 pt-3">
              <Button variant="ghost" size="sm" asChild className="h-8 px-2 sm:px-3 text-xs sm:text-sm">
                <Link href={`/dashboard/results/${result.id}`}>
                  View
                </Link>
              </Button>
              {isProfitable && (
                <>
                  <Button variant="ghost" size="sm" className="h-8 px-2 sm:px-3 text-xs sm:text-sm gap-1">
                    <FileText className="h-3 w-3" />
                    <span className="hidden xs:inline">Cert</span>
                  </Button>
                  <Button variant="ghost" size="sm" className="h-8 px-2 sm:px-3 text-xs sm:text-sm gap-1">
                    <Share2 className="h-3 w-3" />
                    <span className="hidden xs:inline">Share</span>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

const DEFAULT_STATS: ResultsStats = {
  totalTests: 0,
  profitable: 0,
  profitablePercent: 0,
  bestResult: 0,
  avgPnL: 0,
};

const DEFAULT_FILTERS: ResultFilters = {
  search: "",
  type: "all",
  result: "all",
};

export function ResultsList() {
  const { fetchResults, fetchStats } = useResultsApi();
  const refreshKey = useResultsStore((state) => state.refreshKey);
  const [stats, setStats] = useState<ResultsStats>(DEFAULT_STATS);
  const [results, setResults] = useState<ResultListItem[]>([]);
  const [filters, setFilters] = useState<ResultFilters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [pagination, setPagination] = useState<ResultPagination | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const paramsForRequest = useCallback(() => {
    const params: ResultListParams = {
      page,
      limit: pageSize,
    };
    if (filters.type !== "all") {
      params.type = filters.type;
    }
    if (filters.result === "profitable") {
      params.profitable = true;
    } else if (filters.result === "loss") {
      params.profitable = false;
    }
    if (filters.search) {
      params.search = filters.search;
    }
    if (filters.agentId) {
      params.agentId = filters.agentId;
    }
    return params;
  }, [filters, page]);

  const loadStats = useCallback(async () => {
    try {
      const response = await fetchStats();
      const payload = response.stats;
      setStats({
        totalTests: payload.total_tests ?? 0,
        profitable: payload.profitable ?? 0,
        profitablePercent: Math.round(payload.profitable_pct ?? 0),
        bestResult: payload.best_result ?? 0,
        avgPnL: payload.avg_pnl ?? 0,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stats");
    }
  }, [fetchStats]);

  const loadResults = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchResults(paramsForRequest());
      setResults(response.results);
      setPagination(response.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load results");
    } finally {
      setIsLoading(false);
    }
  }, [fetchResults, paramsForRequest]);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  useEffect(() => {
    void loadResults();
  }, [loadResults]);

  // Refresh when refreshKey changes (triggered by store)
  // Only depend on refreshKey, not the callbacks, to avoid infinite loops
  useEffect(() => {
    if (refreshKey > 0) {
      void loadStats();
      void loadResults();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  const handleSearchChange = (value: string) => {
    setFilters((prev) => ({ ...prev, search: value }));
    setPage(1);
  };

  const handleTypeFilter = (value: ResultFilters["type"]) => {
    setFilters((prev) => ({ ...prev, type: value }));
    setPage(1);
  };

  const handleResultFilter = (value: ResultFilters["result"]) => {
    setFilters((prev) => ({ ...prev, result: value }));
    setPage(1);
  };

  const totalResults = pagination?.total ?? results.length;
  const totalPages = pagination?.totalPages ?? (totalResults > 0 ? Math.ceil(totalResults / pageSize) : 1);
  const startIndex = totalResults === 0 ? 0 : (page - 1) * pageSize + 1;
  const endIndex = totalResults === 0 ? 0 : Math.min(page * pageSize, totalResults);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start sm:items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted/50">
            <BarChart3 className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="min-w-0">
            <h1 className="font-mono text-xl sm:text-2xl font-bold">Results & Certificates</h1>
            <p className="text-xs sm:text-sm text-muted-foreground">
              View your test history and download certificates
            </p>
          </div>
        </div>
      </div>

      {/* Aggregate Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Total Tests</p>
            <p className="mt-1 font-mono text-2xl font-bold">{stats.totalTests}</p>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Profitable</p>
            <p className="mt-1 font-mono text-2xl font-bold text-[hsl(var(--accent-green))]">
              {stats.profitable} ({stats.profitablePercent}%)
            </p>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Best Result</p>
            <p className="mt-1 font-mono text-2xl font-bold text-[hsl(var(--accent-green))]">
              +{stats.bestResult}%
            </p>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Avg PnL</p>
            <p className="mt-1 font-mono text-2xl font-bold text-[hsl(var(--accent-green))]">
              {stats.avgPnL >= 0 ? "+" : ""}{stats.avgPnL.toFixed(2)}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row sm:flex-wrap items-stretch sm:items-center gap-3">
        <div className="relative flex-1 min-w-0 sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by agent..."
            value={filters.search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-3">
          <AnimatedSelect value={filters.type} onValueChange={(value) => handleTypeFilter(value as ResultFilters["type"])}>
            <AnimatedSelectTrigger className="flex-1 sm:w-[150px]">
              <AnimatedSelectValue placeholder="Type" />
            </AnimatedSelectTrigger>
            <AnimatedSelectContent>
              <AnimatedSelectItem value="all">All Types</AnimatedSelectItem>
              <AnimatedSelectItem value="backtest">Backtest</AnimatedSelectItem>
              <AnimatedSelectItem value="forward">Forward Test</AnimatedSelectItem>
            </AnimatedSelectContent>
          </AnimatedSelect>
          <AnimatedSelect
            value={filters.result}
            onValueChange={(value) => handleResultFilter(value as ResultFilters["result"])}
          >
            <AnimatedSelectTrigger className="flex-1 sm:w-[150px]">
              <AnimatedSelectValue placeholder="Result" />
            </AnimatedSelectTrigger>
            <AnimatedSelectContent>
              <AnimatedSelectItem value="all">All Results</AnimatedSelectItem>
              <AnimatedSelectItem value="profitable">Profitable</AnimatedSelectItem>
              <AnimatedSelectItem value="loss">Loss</AnimatedSelectItem>
            </AnimatedSelectContent>
          </AnimatedSelect>
        </div>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        {error ? (
          <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        ) : isLoading ? (
          Array.from({ length: 3 }).map((_, idx) => (
            <Card key={idx} className="border-border/50 bg-card/30">
              <CardContent className="h-24 animate-pulse rounded-md bg-muted/30" />
            </Card>
          ))
        ) : results.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <BarChart3 className="mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="font-mono text-lg font-medium">No results found</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Try adjusting your filters or run some tests
            </p>
          </div>
        ) : (
          results.map((result) => <ResultCard key={result.id} result={result} />)
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-muted-foreground">
          <span className="order-2 sm:order-1">
            Showing {startIndex}-{endIndex} of {totalResults}
          </span>
          <div className="flex items-center gap-2 order-1 sm:order-2 w-full sm:w-auto justify-center sm:justify-end">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage(Math.max(1, page - 1))}
            >
              <ChevronLeft className="h-4 w-4 sm:mr-1" />
              <span className="hidden sm:inline">Prev</span>
            </Button>
            <span className="px-2 whitespace-nowrap">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page === totalPages}
              onClick={() => setPage(Math.min(totalPages, page + 1))}
            >
              <span className="hidden sm:inline">Next</span>
              <ChevronRight className="h-4 w-4 sm:ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
