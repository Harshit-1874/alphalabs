"use client";

import { useEffect, useMemo } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger, useSidebar } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/sidebar/app-sidebar";
import { Separator } from "@/components/ui/separator";
import { usePathname } from "next/navigation";
import { useUIStore, useArenaStore, useAgentsStore } from "@/lib/stores";
import type { LiveSessionData } from "@/lib/stores/dynamic-island-store";
import { GlobalDynamicIsland } from "@/components/ui/global-dynamic-island";
import { useDynamicIslandDemoRotation } from "@/lib/use-dynamic-island-demo-rotation";
import type { AccentColor } from "@/types";
import {
  DashboardDataProvider,
  useDashboardDataContext,
} from "@/components/providers/dashboard-data-provider";
import { GlobalBacktestStream } from "@/components/providers/global-backtest-stream";
import { ActiveSessionsProvider } from "@/components/providers/active-sessions-provider";

// Accent color mappings to HSL values
const accentColorMap: Record<AccentColor, { primary: string; ring: string }> = {
  cyan: { primary: "14 94% 48%", ring: "14 94% 48%" },      // Flame Orange (default brand)
  purple: { primary: "263 70% 60%", ring: "263 70% 60%" },  // Lavender Purple
  green: { primary: "142 71% 45%", ring: "142 71% 45%" },   // Green
  amber: { primary: "38 92% 50%", ring: "38 92% 50%" },     // Amber/Cream
};

// Map routes to page titles
const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/dashboard/agents": "My Agents",
  "/dashboard/agents/new": "Create New Agent",
  "/dashboard/arena/backtest": "Backtest Arena",
  "/dashboard/arena/forward": "Forward Test Arena",
  "/dashboard/results": "Results & Certificates",
  "/dashboard/settings": "Settings",
  "/dashboard/settings/api-keys": "API Keys",
  "/dashboard/settings/preferences": "Preferences",
};

// Keyboard shortcuts handler - must be inside SidebarProvider
function KeyboardShortcuts() {
  const { toggleSidebar } = useSidebar();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + B to toggle sidebar
      if ((e.metaKey || e.ctrlKey) && e.key === "b") {
        e.preventDefault();
        toggleSidebar();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleSidebar]);

  return null;
}

// Apply accent color to CSS variables
function AccentColorProvider() {
  const { accentColor } = useUIStore();

  useEffect(() => {
    const colors = accentColorMap[accentColor];
    if (colors) {
      document.documentElement.style.setProperty("--primary", colors.primary);
      document.documentElement.style.setProperty("--ring", colors.ring);
      document.documentElement.style.setProperty("--sidebar-primary", colors.primary);
      document.documentElement.style.setProperty("--sidebar-ring", colors.ring);
    }
  }, [accentColor]);

  return null;
}

function DashboardLayoutInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isDashboardRoot = pathname === "/dashboard";
  const isBacktestConfig = pathname === "/dashboard/arena/backtest";
  const isForwardConfig = pathname === "/dashboard/arena/forward";
  const isBattlePage = pathname.startsWith("/dashboard/arena/backtest/") || pathname.startsWith("/dashboard/arena/forward/");
  const isAgentsPage = pathname.startsWith("/dashboard/agents");
  const isResultsPage = pathname.startsWith("/dashboard/results");
  const isCertsPage = pathname.startsWith("/dashboard/certs");
  const { stats, averageProfit, activity } = useDashboardDataContext();

  // Get active session data for Dynamic Island
  const activeSessionId = useArenaStore((state) => state.activeSessionId);
  const sessionData = useArenaStore((state) => state.sessionData);
  const backtestConfig = useArenaStore((state) => state.backtestConfig);
  const agents = useAgentsStore((state) => state.agents);

  // Determine rotation context and preparing message:
  // - Dashboard root, Agents, Results, Certs: show dashboard rotation
  // - Config pages: show static preparing message
  // - Battle/Live pages: null (let battle-screen.tsx control the island)
  const rotationContext = (isDashboardRoot || isAgentsPage || isResultsPage || isCertsPage)
    ? ("dashboard" as const)
    : null;

  const preparingConfig = useMemo(() => {
    // Only show preparing on config pages (not on battle/live pages)
    if (isBacktestConfig && !isBattlePage) return { type: "backtest" as const };
    if (isForwardConfig && !isBattlePage) return { type: "forward" as const };
    return undefined;
  }, [isBacktestConfig, isForwardConfig, isBattlePage]);

  const rotationData = useMemo(() => {
    if (!stats) return undefined;

    // Build live session data if there's an active session
    let liveSession: LiveSessionData | undefined;
    if (activeSessionId && sessionData[activeSessionId]) {
      const session = sessionData[activeSessionId];
      const agent = agents.find((a) => a.id === backtestConfig?.agentId);
      const startTime = session.startedAt ? new Date(session.startedAt).getTime() : Date.now();
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      const duration = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;

      liveSession = {
        agentName: agent?.name || "AI Agent",
        pnl: session.pnl || 0,
        duration,
        status: session.status === "running" ? "running" : "paused",
        sessionId: activeSessionId,
        sessionType: "backtest",
        totalTrades: session.trades?.length || 0,
        equity: session.equity,
        winRate: session.winRate,
      };
    }

    return {
      stats: {
        totalAgents: stats.totalAgents,
        testsRun: stats.testsRun,
        bestAgentName: stats.bestAgent?.name,
      },
      avgPnL: stats.bestPnL ?? averageProfit ?? null,
      winRate: stats.trends.winRateChange ?? null,
      activity: activity.length
        ? {
          agentName: activity[0].agentName ?? "Agent",
          description: activity[0].description,
          pnl: activity[0].pnl ?? undefined,
          resultId: activity[0].resultId ?? undefined,
        }
        : undefined,
      liveSession,
    };
  }, [stats, averageProfit, activity, activeSessionId, sessionData, backtestConfig, agents]);

  useDynamicIslandDemoRotation(rotationContext, preparingConfig, rotationData);

  const getPageTitle = () => {
    if (pageTitles[pathname]) return pageTitles[pathname];

    if (pathname.startsWith("/dashboard/agents/") && pathname.includes("/edit")) {
      return "Edit Agent";
    }
    if (pathname.startsWith("/dashboard/agents/") && !pathname.includes("/new")) {
      return "Agent Details";
    }
    if (pathname.startsWith("/dashboard/arena/backtest/")) {
      return "Backtest Battle";
    }
    if (pathname.startsWith("/dashboard/arena/forward/")) {
      return "Live Session";
    }
    if (pathname.startsWith("/dashboard/results/")) {
      return "Test Result";
    }

    return "Dashboard";
  };

  return (
    <SidebarProvider>
      <KeyboardShortcuts />
      <AccentColorProvider />
      <GlobalDynamicIsland
        totalAgents={stats?.totalAgents ?? 0}
        averageProfit={averageProfit ?? undefined}
      />
      <AppSidebar />
      <SidebarInset>
        {/* Top Header Bar */}
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <span className="font-mono text-sm font-medium text-muted-foreground">
              {getPageTitle()}
            </span>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto">
          <div className="container max-w-[1400px] mx-auto px-3 py-4 sm:px-4 sm:py-6 md:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardDataProvider>
      <ActiveSessionsProvider>
        <DashboardLayoutInner>
          <GlobalBacktestStream />
          {children}
        </DashboardLayoutInner>
      </ActiveSessionsProvider>
    </DashboardDataProvider>
  );
}

