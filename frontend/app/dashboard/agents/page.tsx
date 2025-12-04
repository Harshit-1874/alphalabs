"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { AgentsPageHeader } from "@/components/agents/agents-page-header";
import { AgentsView } from "@/components/agents/agents-view";
import { PageTransition } from "@/components/ui/page-transition";
import { useAgents } from "@/hooks/use-agents";

export default function AgentsPage() {
  const pathname = usePathname();
  const [showArchived, setShowArchived] = useState(false);
  const { refetch } = useAgents(undefined, showArchived);

  // Refresh agents when navigating to this page (showArchived changes are handled by useAgents hook)
  useEffect(() => {
    if (pathname === "/dashboard/agents") {
      void refetch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const handleToggleArchived = () => {
    setShowArchived(!showArchived);
  };

  return (
    <PageTransition className="space-y-6">
      {/* Page Header */}
      <AgentsPageHeader 
        showArchived={showArchived}
        onToggleArchived={handleToggleArchived}
      />
      
      {/* Agents Grid/List View */}
      <AgentsView showArchived={showArchived} />
    </PageTransition>
  );
}

