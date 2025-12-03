import { LiveSessionView } from "@/components/arena/forward/live-session-view";
import { PageTransition } from "@/components/ui/page-transition";

interface Props {
  params: Promise<{ sessionId: string }>;
}

export default async function ForwardTestLivePage({ params }: Props) {
  const { sessionId } = await params;
  
  return (
    <PageTransition>
      <LiveSessionView sessionId={sessionId} />
    </PageTransition>
  );
}

