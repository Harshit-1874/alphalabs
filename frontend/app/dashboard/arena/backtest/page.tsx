import { BacktestConfig } from "@/components/arena/backtest/backtest-config";
import { PageTransition } from "@/components/ui/page-transition";

export default function BacktestPage() {
  return (
    <PageTransition>
      <BacktestConfig />
    </PageTransition>
  );
}

