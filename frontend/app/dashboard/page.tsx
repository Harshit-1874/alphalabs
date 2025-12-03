import { DashboardHeader } from "@/components/dashboard/dashboard-header";
import { StatsCardRow } from "@/components/dashboard/stats-card-row";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { LiveSessionsPanel } from "@/components/dashboard/live-sessions-panel";
import { QuickStartGuide } from "@/components/dashboard/quick-start-guide";
import { PageTransition } from "@/components/ui/page-transition";

export default function DashboardPage() {
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

