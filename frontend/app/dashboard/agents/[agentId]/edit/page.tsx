import { AgentEditWizard } from "@/components/agents/creation/agent-edit-wizard";
import { PageTransition } from "@/components/ui/page-transition";

interface EditAgentPageProps {
  params: Promise<{ agentId: string }>;
}

export default async function EditAgentPage({ params }: EditAgentPageProps) {
  const { agentId } = await params;
  
  return (
    <PageTransition>
      <AgentEditWizard agentId={agentId} />
    </PageTransition>
  );
}

