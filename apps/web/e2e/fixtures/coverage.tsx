import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { coverageGapAssessment, coverageGapCase } from "../../src/fixtures/coverageCase";
import { AssessmentView } from "../../src/features/cases/Assessment";
import { PrintReport } from "../../src/features/cases/PrintReport";
import "../../src/index.css";

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={new QueryClient()}>
    <main className="mx-auto max-w-4xl p-5 md:p-10">
      <p className="mb-4 text-sm text-ink-2">Coverage test fixture · fictional policies · no model call</p>
      <AssessmentView assessment={coverageGapAssessment} facts={coverageGapCase.facts}
        agentMessages={[]} onOpenEvidence={() => {}} reveal={false} />
      <PrintReport detail={coverageGapCase} />
    </main>
  </QueryClientProvider>,
);
