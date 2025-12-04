"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { DashboardHeader } from "@/components/dashboard/dashboard-header";
import { StatsCardRow } from "@/components/dashboard/stats-card-row";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { LiveSessionsPanel } from "@/components/dashboard/live-sessions-panel";
import { QuickStartGuide } from "@/components/dashboard/quick-start-guide";
import { PageTransition } from "@/components/ui/page-transition";
import { useDashboardDataContext } from "@/components/providers/dashboard-data-provider";

export default function DashboardPage() {
  const { refresh } = useDashboardDataContext();
  const pathname = usePathname();

  // Refresh dashboard data when navigating to this page
  useEffect(() => {
    if (pathname === "/dashboard") {
      void refresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  return (
    <PageTransition className="space-y-4 sm:space-y-6">
      {/* Page Header */}
      <DashboardHeader />

      {/* Stats Cards Row */}
      <StatsCardRow />

      {/* Main Content Grid - stack on mobile, side-by-side on desktop */}
      <div className="grid gap-4 sm:gap-6 lg:grid-cols-[1fr_350px] xl:grid-cols-[1fr_400px]">
        {/* Recent Activity */}
        <RecentActivity />

        {/* Live Sessions Panel */}
        <LiveSessionsPanel />
      </div>

      {/* Quick Start Guide (for new users) */}
      <QuickStartGuide />
    </PageTransition>
  );
}

