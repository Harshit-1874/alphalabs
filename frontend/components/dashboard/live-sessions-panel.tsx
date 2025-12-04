"use client";

import { Radio, ArrowRight, Pause, Play } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useArenaStore } from "@/lib/stores";

interface HappeningSession {
  id: string;
  agentName: string;
  asset: string;
  pnl: number;
  progress: number;
  status: string;
}

function LiveSessionCard({ session }: { session: HappeningSession }) {
  return (
    <div className="rounded-lg border border-border/50 bg-card/50 p-4">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="status-dot status-dot-live" />
          <span className="font-mono text-sm font-semibold">{session.agentName}</span>
        </div>
        <Badge className="bg-[hsl(var(--accent-green)/0.15)] text-[hsl(var(--accent-green))] hover:bg-[hsl(var(--accent-green)/0.2)]">
          LIVE
        </Badge>
      </div>

      {/* Stats Grid */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Asset</p>
          <p className="font-mono text-sm font-medium">
            {session.asset.toUpperCase().replace("-", "/")}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">PnL</p>
          <p
            className={cn(
              "font-mono text-sm font-medium",
              session.pnl >= 0 ? "text-[hsl(var(--accent-green))]" : "text-[hsl(var(--accent-red))]"
            )}
          >
            {session.pnl >= 0 ? "+" : ""}
            {session.pnl.toFixed(2)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Progress</p>
          <p className="font-mono text-sm font-medium">{session.progress.toFixed(0)}%</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Status</p>
          <p className="font-mono text-sm font-medium capitalize">{session.status}</p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button asChild size="sm" className="flex-1 gap-1">
          <Link href={`/dashboard/arena/backtest/${session.id}`}>
            View
            <ArrowRight className="h-3 w-3" />
          </Link>
        </Button>
        <Button variant="ghost" size="sm" className="gap-1" disabled>
          {session.status === "running" ? (
            <>
              <Pause className="h-3 w-3" />
              Pause
            </>
          ) : (
            <>
              <Play className="h-3 w-3" />
              Resume
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="relative mb-4">
        <div className="rounded-full bg-muted/50 p-4">
          <Radio className="h-8 w-8 text-muted-foreground" />
        </div>
        {/* Pulse animation rings */}
        <div className="absolute inset-0 animate-ping rounded-full bg-muted/20" />
      </div>
      <h3 className="font-mono text-base font-medium">No active sessions</h3>
      <p className="mt-1 max-w-[200px] text-xs text-muted-foreground">
        Start a Forward Test to see live trading
      </p>
      <Button asChild className="mt-4 gap-1" size="sm">
        <Link href="/dashboard/arena/forward">
          Start Test
          <ArrowRight className="h-3 w-3" />
        </Link>
      </Button>
    </div>
  );
}

export function LiveSessionsPanel() {
  const liveSessions = useArenaStore((state) => state.liveSessions);

  return (
    <Card className="border-border/50 bg-card/30">
      <CardHeader className="pb-4">
        <CardTitle className="font-mono text-lg font-semibold">Live Sessions</CardTitle>
      </CardHeader>
      <CardContent>
        {liveSessions.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-4">
            {liveSessions.map((session) => (
              <LiveSessionCard
                key={session.id}
                session={{
                  id: session.id,
                  agentName: session.agentName || session.agentId || "Agent",
                  asset: session.asset,
                  pnl: session.pnl,
                  progress: (session as any).progress ?? 0,
                  status: session.status,
                }}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

