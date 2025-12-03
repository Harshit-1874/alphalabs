import { ResultsList } from "@/components/results/results-list";
import { PageTransition } from "@/components/ui/page-transition";

export default function ResultsPage() {
  return (
    <PageTransition>
      <ResultsList />
    </PageTransition>
  );
}

