"use client";

import { ArrowRight, Inbox } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ActivityItem {
  id: string;
  type: "backtest_complete" | "backtest_failed" | "agent_created" | "forward_complete";
  agentName: string;
  result?: number; // PnL percentage
  timestamp: string;
  details?: string;
}

// Mock data - in real app would come from API
const mockActivities: ActivityItem[] = [
  {
    id: "1",
    type: "backtest_complete",
    agentName: "α-1",
    result: 23.4,
    timestamp: "2 hours ago",
    details: "Monk Mode • BTC/USDT",
  },
  {
    id: "2",
    type: "backtest_failed",
    agentName: "β-2",
    result: -12.1,
    timestamp: "5 hours ago",
    details: "Omni Mode • ETH/USDT",
  },
  {
    id: "3",
    type: "agent_created",
    agentName: "γ-3",
    timestamp: "Yesterday",
    details: "Monk Mode • Ready for testing",
  },
];

function ActivityItemCard({ activity }: { activity: ActivityItem }) {
  const getStatusColor = () => {
    switch (activity.type) {
      case "backtest_complete":
        return activity.result && activity.result > 0
          ? "bg-[hsl(var(--accent-green))]"
          : "bg-[hsl(var(--accent-red))]";
      case "backtest_failed":
        return "bg-[hsl(var(--accent-red))]";
      case "agent_created":
        return "bg-[hsl(var(--accent-amber))]";
      case "forward_complete":
        return activity.result && activity.result > 0
          ? "bg-[hsl(var(--accent-green))]"
          : "bg-[hsl(var(--accent-red))]";
      default:
        return "bg-muted";
    }
  };

  const getActionLabel = () => {
    switch (activity.type) {
      case "backtest_complete":
      case "backtest_failed":
        return "Backtest Complete";
      case "agent_created":
        return "Agent Created";
      case "forward_complete":
        return "Forward Test Complete";
      default:
        return "Activity";
    }
  };

  const getLinkHref = () => {
    switch (activity.type) {
      case "backtest_complete":
      case "backtest_failed":
      case "forward_complete":
        return `/dashboard/results/${activity.id}`;
      case "agent_created":
        return `/dashboard/agents/${activity.id}/edit`;
      default:
        return "#";
    }
  };

  const getLinkLabel = () => {
    switch (activity.type) {
      case "agent_created":
        return "Edit";
      default:
        return "View";
    }
  };

  return (
    <div className="group rounded-lg border border-border/50 bg-card/30 p-3 sm:p-4 transition-colors hover:bg-muted/30">
      {/* Mobile: Stack layout, Desktop: Flex row */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
        {/* Top row on mobile: Status + Agent Name + Badge */}
        <div className="flex items-center gap-3 sm:flex-1 min-w-0">
          {/* Status Indicator */}
          <div className={cn("h-2 w-2 shrink-0 rounded-full", getStatusColor())} />

          {/* Content */}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-mono text-sm font-medium">{activity.agentName}</span>
              <span className="text-sm text-muted-foreground">{getActionLabel()}</span>
            </div>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground mt-0.5">
              <span>{activity.timestamp}</span>
              {activity.details && (
                <>
                  <span className="hidden xs:inline">•</span>
                  <span className="w-full xs:w-auto">{activity.details}</span>
                </>
              )}
            </div>
          </div>

          {/* Result Badge - visible on mobile in the row */}
          {activity.result !== undefined && (
            <Badge
              variant="outline"
              className={cn(
                "font-mono text-xs shrink-0",
                activity.result > 0
                  ? "border-[hsl(var(--accent-green)/0.3)] bg-[hsl(var(--accent-green)/0.1)] text-[hsl(var(--accent-green))]"
                  : "border-[hsl(var(--accent-red)/0.3)] bg-[hsl(var(--accent-red)/0.1)] text-[hsl(var(--accent-red))]"
              )}
            >
              {activity.result > 0 ? "+" : ""}
              {activity.result}%
            </Badge>
          )}
        </div>

        {/* Action Link - always visible on mobile, hover on desktop */}
        <Link
          href={getLinkHref()}
          className="flex items-center gap-1 text-xs text-muted-foreground sm:opacity-0 transition-opacity group-hover:opacity-100 hover:text-foreground ml-5 sm:ml-0"
        >
          {getLinkLabel()}
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="mb-4 rounded-full bg-muted/50 p-4">
        <Inbox className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="font-mono text-lg font-medium">No activity yet</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Create an agent and run your first test
      </p>
      <Button asChild className="mt-4" size="sm">
        <Link href="/dashboard/agents/new">Create Agent</Link>
      </Button>
    </div>
  );
}

export function RecentActivity() {
  const activities = mockActivities;

  return (
    <Card className="border-border/50 bg-card/30">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <CardTitle className="font-mono text-lg font-semibold">Recent Activity</CardTitle>
        <Link
          href="/dashboard/results"
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          View All
          <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent className="space-y-3">
        {activities.length === 0 ? (
          <EmptyState />
        ) : (
          activities.map((activity) => (
            <ActivityItemCard key={activity.id} activity={activity} />
          ))
        )}
      </CardContent>
    </Card>
  );
}

