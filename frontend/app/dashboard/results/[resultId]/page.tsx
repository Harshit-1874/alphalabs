import { ResultDetail } from "@/components/results/result-detail";
import { PageTransition } from "@/components/ui/page-transition";

interface Props {
  params: Promise<{ resultId: string }>;
}

export default async function ResultDetailPage({ params }: Props) {
  const { resultId } = await params;
  
  return (
    <PageTransition>
      <ResultDetail resultId={resultId} />
    </PageTransition>
  );
}

