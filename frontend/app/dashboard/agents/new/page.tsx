import { AgentCreationWizard } from "@/components/agents/creation/agent-creation-wizard";
import { PageTransition } from "@/components/ui/page-transition";

export default function NewAgentPage() {
  return (
    <PageTransition>
      <AgentCreationWizard />
    </PageTransition>
  );
}

