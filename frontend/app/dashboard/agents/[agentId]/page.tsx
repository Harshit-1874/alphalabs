import { AgentDetailView } from "@/components/agents/detail/agent-detail-view";
import { PageTransition } from "@/components/ui/page-transition";

interface AgentDetailPageProps {
  params: Promise<{ agentId: string }>;
}

export default async function AgentDetailPage({ params }: AgentDetailPageProps) {
  const { agentId } = await params;
  
  return (
    <PageTransition>
      <AgentDetailView agentId={agentId} />
    </PageTransition>
  );
}

