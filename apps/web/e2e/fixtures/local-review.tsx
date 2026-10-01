import { useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { localReviewAssessment, localReviewCase, localReviewQuestions } from "../../src/fixtures/localReviewCase";
import { AssessmentView } from "../../src/features/cases/Assessment";
import { ClarificationBlock } from "../../src/features/cases/Conversation";
import { ExecutionNotice } from "../../src/components/ExecutionNotice";
import { PrintReport } from "../../src/features/cases/PrintReport";
import "../../src/index.css";

function LocalReviewFixture() {
  const [finished, setFinished] = useState(false);
  return <main className="mx-auto max-w-4xl p-5 md:p-10">
    <p className="mb-4 text-sm text-ink-2">Local review UI fixture · no provider calls</p>
    {finished ? <>
      <AssessmentView assessment={localReviewAssessment} facts={localReviewCase.facts} agentMessages={[]} onOpenEvidence={() => {}} reveal={false} />
      <PrintReport detail={localReviewCase} />
    </> : <>
      <ExecutionNotice execution={localReviewAssessment.execution} />
      <ClarificationBlock questions={localReviewQuestions} localReview submitting={false} onSubmit={() => setFinished(true)} onFinishLocal={() => setFinished(true)} onOpenClause={() => {}} />
    </>}
  </main>;
}
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={new QueryClient()}><LocalReviewFixture /></QueryClientProvider>,
);
