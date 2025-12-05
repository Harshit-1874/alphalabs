"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

// ============================================
// Agent Skeletons
// ============================================

export function AgentCardSkeleton() {
  return (
    <Card className="border-border/50 bg-card/50">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
          </div>
          <Skeleton className="h-8 w-8 rounded-md" />
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="rounded-lg border border-border/50 bg-muted/20 p-3 space-y-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-3 w-full" />
        </div>
        <div className="mt-3 flex items-center justify-between">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-12" />
        </div>
      </CardContent>
    </Card>
  );
}

export function AgentListSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <AgentCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function AgentDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <Skeleton className="h-12 w-12 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-20" />
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-28" />
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="border-border/50 bg-card/30">
            <CardContent className="p-4 space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <Card className="border-border/50 bg-card/30">
          <CardContent className="p-6 space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-5/6" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ============================================
// Result Skeletons
// ============================================

export function ResultCardSkeleton() {
  return (
    <Card className="border-border/50 bg-card/50">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
          <div className="text-right space-y-2">
            <Skeleton className="h-5 w-16 ml-auto" />
            <Skeleton className="h-3 w-12 ml-auto" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function ResultListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <ResultCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function ResultDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-28" />
          <Skeleton className="h-9 w-24" />
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="border-border/50 bg-card/30">
            <CardContent className="p-4 space-y-2">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-6 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Chart */}
      <Card className="border-border/50 bg-card/30">
        <CardContent className="p-4">
          <Skeleton className="h-[300px] w-full rounded-lg" />
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================
// Dashboard Skeletons
// ============================================

export function StatsCardSkeleton() {
  return (
    <Card className="border-border/50 bg-card/30">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-2 flex-1">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-16" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function DashboardStatsSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <StatsCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function ActivitySkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 rounded-lg border border-border/50 bg-card/30 p-4">
          <Skeleton className="h-2 w-2 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="h-6 w-12" />
        </div>
      ))}
    </div>
  );
}

// ============================================
// Chart Skeletons
// ============================================

// ============================================
// Table Skeletons
// ============================================

export function TableRowSkeleton() {
  return (
    <div className="flex items-center gap-4 py-3 border-b border-border/50">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-4 w-16" />
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-4 w-12 ml-auto" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="w-full">
      <div className="flex items-center gap-4 py-3 border-b border-border">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-12 ml-auto" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <TableRowSkeleton key={i} />
      ))}
    </div>
  );
}

// ============================================
// Page-level Loading Components
// ============================================

export function PageLoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      
      {/* Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <Skeleton className="h-[400px] w-full rounded-lg" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-48 w-full rounded-lg" />
          <Skeleton className="h-48 w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}

// ============================================
// Battle Screen Skeletons
// ============================================

export function BattleScreenSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-24" />
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="border-border/50 bg-card/30">
            <CardContent className="p-4 space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-24" />
              <Skeleton className="h-3 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chart Section */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-[500px] w-full rounded-lg" />
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Thoughts */}
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <Skeleton className="h-6 w-24" />
            </CardHeader>
            <CardContent className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="space-y-2 p-3 border border-border/30 rounded-lg">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-20" />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Trades */}
          <Card className="border-border/50 bg-card/30">
            <CardHeader>
              <Skeleton className="h-6 w-24" />
            </CardHeader>
            <CardContent className="space-y-3">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="space-y-2 p-3 border border-border/30 rounded-lg">
                  <div className="flex justify-between">
                    <Skeleton className="h-4 w-16" />
                    <Skeleton className="h-4 w-20" />
                  </div>
                  <Skeleton className="h-3 w-full" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <div className="w-full" style={{ height: `${height}px` }}>
      <Skeleton className="h-full w-full rounded-lg" />
    </div>
  );
}

export function StatsRowSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i} className="border-border/50 bg-card/30">
          <CardContent className="p-4 space-y-2">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-3 w-16" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

