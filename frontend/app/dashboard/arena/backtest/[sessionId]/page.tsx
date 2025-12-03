import { BattleScreen } from "@/components/arena/backtest/battle-screen";
import { PageTransition } from "@/components/ui/page-transition";

interface Props {
  params: Promise<{ sessionId: string }>;
}

export default async function BacktestBattlePage({ params }: Props) {
  const { sessionId } = await params;
  
  return (
    <PageTransition>
      <BattleScreen sessionId={sessionId} />
    </PageTransition>
  );
}

