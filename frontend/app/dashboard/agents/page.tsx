import { AgentsPageHeader } from "@/components/agents/agents-page-header";
import { AgentsView } from "@/components/agents/agents-view";
import { PageTransition } from "@/components/ui/page-transition";

export default function AgentsPage() {
  return (
    <PageTransition className="space-y-6">
      {/* Page Header */}
      <AgentsPageHeader />
      
      {/* Agents Grid/List View */}
      <AgentsView />
    </PageTransition>
  );
}

