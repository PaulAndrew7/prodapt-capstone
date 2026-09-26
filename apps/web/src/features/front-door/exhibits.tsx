/*
  Front-door exhibits. Each is built from the real app components with fixture data,
  so what the page shows is what the product does. Timelines are module constants.
*/
import { useRef, useState } from "react";
import { AnimatePresence } from "motion/react";
import { ArrowsLeftRight, MagnifyingGlass } from "@phosphor-icons/react";
import type { AgentRole } from "@/lib/api/types";
import { AppHeader } from "@/app/AppShell";
import { CaseHeader } from "@/features/cases/CaseWorkspace";
import { ClarificationBlock, DONT_KNOW, FactList, Transcript } from "@/features/cases/Conversation";
import { AssessmentView } from "@/features/cases/Assessment";
import { EvidenceDrawer } from "@/features/cases/EvidenceDrawer";
import { LookupAnswerView } from "@/features/policies/PolicyAsk";
import { ClauseBody } from "@/features/policies/PolicyDetail";
import { VersionDiff } from "@/features/policies/VersionDiff";
import { ReviewForm } from "@/features/review/ReviewQueue";
import { StageTrack } from "@/components/StageTrack";
import { RequirementStatusWord, VerdictHeadline } from "@/components/Status";
import { Skeleton } from "@/components/Feedback";
import { STAGES, type StageStatus } from "@/lib/events/runStore";
import {
  vendorCaseComplete,
  vendorFactsInitial,
  vendorHypothetical,
  vendorHypotheticalChanges,
  vendorQuestions,
} from "@/fixtures/vendorCase";
import { lookupAnswer } from "@/fixtures/lookup";
import { policyVersions } from "@/fixtures/policies";
import { Exhibit, useExhibitScript } from "./Exhibit";

const noop = () => {};
const vendor = vendorCaseComplete;
const assessment = vendor.assessment!;

/* E1: the whole case workspace, then the evidence drawer opening on clause 4.2. */
const E1_TIMELINE = [700, 2400];
export function WorkspaceExhibit() {
  const ref = useRef<HTMLDivElement>(null);
  const { step, replay } = useExhibitScript(ref, E1_TIMELINE);
  const finding = assessment.findings[0];
  return (
    <Exhibit
      frameRef={ref}
      label="The case workspace for the vendor case: the verdict Non-compliant, four findings, and the evidence for clause 4.2 opening beside them."
      caption="The case workspace, playing a sample case with fictional policies."
      onReplay={replay}
    >
      <div className="flex h-full flex-col bg-paper">
        <AppHeader sticky={false} activePath="/app/cases" />
        <CaseHeader
          detail={vendor}
          phase="completed"
          onHypothetical={noop}
          hypotheticalOpen={false}
          onCancel={noop}
          canceling={false}
        />
        <div className="grid min-h-0 flex-1 grid-cols-[38fr_62fr]">
          <div className="space-y-10 overflow-hidden border-r-2 border-ink px-8 py-8">
            <Transcript messages={vendor.messages.slice(0, 1)} autoScroll={false} />
            <FactList facts={vendor.facts} />
          </div>
          <div className="relative overflow-hidden bg-sheet">
            <div className="px-10 py-10">
              {step === 0 ? (
                <div className="space-y-6">
                  <StageTrack stages={Object.fromEntries(STAGES.map((s) => [s.role, "done"])) as Record<AgentRole, StageStatus>} />
                  <Skeleton className="h-16 w-3/5" />
                  <Skeleton className="h-5 w-4/5" />
                </div>
              ) : (
                <AssessmentView
                  key={`e1-${step > 0}`}
                  assessment={assessment}
                  facts={vendor.facts}
                  agentMessages={vendor.agent_messages}
                  onOpenEvidence={noop}
                  reveal
                />
              )}
            </div>
            <AnimatePresence>
              {step >= 2 && (
                <EvidenceDrawer
                  title={finding.title}
                  status={finding.status}
                  citations={assessment.citations.filter((c) => c.id === "cite_1")}
                  focusCitationId="cite_1"
                  onClose={noop}
                />
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </Exhibit>
  );
}

/* E2: a plain policy question, answered with the clauses behind it. */
const E2_TIMELINE = [600, 900];
export function LookupExhibit() {
  const ref = useRef<HTMLDivElement>(null);
  const { step } = useExhibitScript(ref, E2_TIMELINE);
  return (
    <Exhibit frameRef={ref} width={1000} height={600} label="A policy question answered in two sentences, with the two supporting clauses and their exact words highlighted.">
      <div className="h-full bg-paper p-10">
        <p className="font-display text-3xl font-semibold">Ask a policy question</p>
        <div className="relative mt-4">
          <MagnifyingGlass size={18} aria-hidden className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-2" />
          <div className="flex h-12 items-center border-2 border-ink bg-sheet pl-10 pr-3">{lookupAnswer.question}</div>
        </div>
        <div className="mt-8">
          {step === 0 ? null : step === 1 ? (
            <div className="space-y-3">
              <Skeleton className="h-6 w-4/5" />
              <Skeleton className="h-6 w-3/5" />
            </div>
          ) : (
            <LookupAnswerView answer={lookupAnswer} />
          )}
        </div>
      </div>
    </Exhibit>
  );
}

/* E3: five roles run, then the verdict arrives. Stage states come from the same component the app uses. */
const E3_TIMELINE = [500, 800, 1000, 700, 900, 700, 500];
function stagesAt(step: number): Record<AgentRole, StageStatus> {
  const out = {} as Record<AgentRole, StageStatus>;
  STAGES.forEach((s, i) => {
    out[s.role] = step - 1 > i ? "done" : step - 1 === i ? "active" : "pending";
  });
  return out;
}
export function AssessExhibit() {
  const ref = useRef<HTMLDivElement>(null);
  const { step } = useExhibitScript(ref, E3_TIMELINE);
  const done = step >= E3_TIMELINE.length;
  return (
    <Exhibit frameRef={ref} width={1000} height={700} label="An assessment running through retrieve, analyze, assess risk, validate and recommend, then showing the verdict Non-compliant with its findings.">
      <div className="h-full bg-sheet p-10">
        <p className="max-w-[60ch] text-ink-2">&ldquo;{vendor.scenario_text}&rdquo;</p>
        <div className="mt-8">
          <StageTrack stages={stagesAt(step)} />
        </div>
        <div className="mt-10">
          {done ? (
            <>
              <VerdictHeadline status="non_compliant" />
              <p className="mt-3 max-w-[52ch] text-xl leading-snug">{assessment.summary}</p>
              <ul className="mt-8 divide-y divide-rule border-y-2 border-ink">
                {assessment.findings.slice(0, 3).map((f, i) => (
                  <li key={f.id} className="grid grid-cols-[2.5rem_minmax(0,1fr)_auto] items-baseline gap-4 py-3">
                    <span className="tnum font-display text-2xl font-bold">{i + 1}</span>
                    <span className="font-medium">{f.title}</span>
                    <RequirementStatusWord status={f.status} />
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <div className="space-y-5">
              <Skeleton className="h-16 w-3/5" />
              <Skeleton className="h-5 w-4/5" />
              <Skeleton className="h-5 w-2/3" />
            </div>
          )}
        </div>
      </div>
    </Exhibit>
  );
}

/* E4: the policy itself, with the cited words marked. */
const E4_TIMELINE = [700];
export function EvidenceExhibit() {
  const ref = useRef<HTMLDivElement>(null);
  const { step } = useExhibitScript(ref, E4_TIMELINE);
  const v = policyVersions.ds_v1;
  const clauses = v.clauses.filter((c) => ["4.1", "4.2", "4.3"].includes(c.section_path[c.section_path.length - 1]));
  const quote = assessment.citations[0].quote;
  return (
    <Exhibit frameRef={ref} width={1000} height={700} label="Clause 4.2 of the Customer Data Sharing Policy, with the exact words that support the finding highlighted.">
      <div className="h-full bg-paper px-12 py-10">
        <p className="font-display text-4xl font-bold">{v.policy_title}</p>
        <p className="tnum mt-1 text-sm text-ink-2">v1, effective 1 Jan 2026</p>
        <div className="mt-6 border-t-2 border-ink">
          {clauses.map((c) => (
            <div key={c.id} className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-x-6 py-6">
              <ClauseBody clause={c} quote={c.section_path.includes("4.2") ? quote : null} play={step >= 1} headingLevel="p" />
            </div>
          ))}
        </div>
      </div>
    </Exhibit>
  );
}

/* E5: drag between the real case and a hypothetical branch. The only interactive exhibit. */
function ResultPanel({ side, a }: { side: "real" | "hypothetical"; a: typeof assessment }) {
  const right = side === "hypothetical";
  return (
    <div className="h-full bg-sheet p-10">
      <div className={right ? "ml-auto w-[45%] text-right" : "w-[45%]"}>
        <VerdictHeadline status={a.status} reveal={false} size="md" as="p" />
        <ul className="mt-6 divide-y divide-rule border-y-2 border-ink text-left">
          {a.findings.map((f) => (
            <li key={f.id} className={right ? "flex flex-row-reverse items-baseline justify-between gap-4 py-3" : "flex items-baseline justify-between gap-4 py-3"}>
              <span className="font-medium">{f.title}</span>
              <RequirementStatusWord status={f.status} className="shrink-0" />
            </li>
          ))}
        </ul>
        {right && (
          <ul className="mt-5 space-y-1 text-sm">
            {vendorHypotheticalChanges.map((c) => (
              <li key={c.label}>
                <span className="font-semibold">{c.label}:</span> {c.to}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function HypotheticalExhibit() {
  const [pct, setPct] = useState(50);
  return (
    <div className="relative">
      <div className="relative">
        <Exhibit width={1100} height={600} label="Real case: Non-compliant. Hypothetical branch with approval recorded, vendor approved and fields documented: Compliant within scope.">
          <div className="relative h-full">
            <ResultPanel side="real" a={assessment} />
            <div className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${pct}%)` }}>
              <ResultPanel side="hypothetical" a={vendorHypothetical} />
            </div>
            <div className="absolute inset-y-0 w-[3px] -translate-x-1/2 bg-ink" style={{ left: `${pct}%` }} />
          </div>
        </Exhibit>
        <div
          aria-hidden
          className="pointer-events-none absolute bottom-6 flex h-11 -translate-x-1/2 items-center gap-3 whitespace-nowrap bg-mark px-4 text-sm font-semibold text-on-mark"
          style={{ left: `${Math.min(84, Math.max(16, pct))}%` }}
        >
          Real case
          <ArrowsLeftRight size={20} />
          Hypothetical
        </div>
        <label htmlFor="compare-range" className="sr-only">
          Drag to compare the real case with the hypothetical branch
        </label>
        <input
          id="compare-range"
          type="range"
          min={4}
          max={96}
          value={pct}
          onChange={(e) => setPct(Number(e.target.value))}
          className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
        />
      </div>
      <p className="mt-3 text-sm text-ink-2">Drag to compare. The hypothetical is a separate branch; the real case never changes.</p>
    </div>
  );
}

/* E6: the questions that decide the case, and the facts with their three states. */
export function ClarificationExhibit() {
  return (
    <Exhibit width={880} height={900} label="Two clarifying questions, each with a reason and an I don't know option, above a list of facts marked provided, inferred or unknown.">
      <div className="h-full space-y-10 bg-paper p-10">
        <ClarificationBlock
          questions={vendorQuestions}
          onSubmit={noop}
          submitting={false}
          onOpenClause={noop}
          initialAnswers={{ q_vendor_review: DONT_KNOW, q_fields: "Customer ID, postcode and product holdings, for churn modelling." }}
        />
        <FactList facts={vendorFactsInitial} />
      </div>
    </Exhibit>
  );
}

/* E8: v1 to v2, the added retention clause marked. */
const E8_TIMELINE = [600];
export function VersionExhibit() {
  const ref = useRef<HTMLDivElement>(null);
  const { step } = useExhibitScript(ref, E8_TIMELINE);
  return (
    <Exhibit frameRef={ref} width={720} height={330} label="Customer Data Sharing Policy version 1 compared with version 2: clause 4.5 on retention periods was added.">
      <div className="h-full bg-paper p-10">
        <p className="font-display text-3xl font-semibold">What changed</p>
        <div className="mt-4">
          <VersionDiff from={policyVersions.ds_v1} to={policyVersions.ds_v2} play={step >= 1} />
        </div>
      </div>
    </Exhibit>
  );
}

/* E9: the reviewer's side of the same case. */
export function ReviewExhibit() {
  return (
    <Exhibit width={900} height={790} label="A reviewer panel showing the vendor case verdict, its findings, and accept, challenge or request information options with a required rationale.">
      <div className="h-full bg-sheet p-10">
        <VerdictHeadline status="non_compliant" size="md" reveal={false} as="p" />
        <p className="mt-2 font-semibold">{vendor.title}</p>
        <ul className="mt-6 divide-y divide-rule border-y-2 border-ink">
          {assessment.findings.slice(0, 3).map((f, i) => (
            <li key={f.id} className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-baseline gap-4 py-3">
              <span className="tnum font-display text-xl font-bold">{i + 1}</span>
              <span className="font-medium">{f.title}</span>
              <RequirementStatusWord status={f.status} />
            </li>
          ))}
        </ul>
        <ReviewForm detail={vendor} />
      </div>
    </Exhibit>
  );
}

/* E10: the export is plain JSON that keeps provenance; show its real opening lines. */
export function ExportExcerpt() {
  const excerpt = JSON.stringify(
    {
      status: assessment.status,
      policy_snapshot_id: assessment.policy_snapshot_id,
      citation: {
        clause_id: assessment.citations[0].clause_id,
        page_index: assessment.citations[0].page_index,
        quote: assessment.citations[0].quote.slice(0, 34) + "...",
      },
      review_state: assessment.review_state,
    },
    null,
    2,
  );
  return (
    <pre aria-label="Opening lines of an exported assessment in JSON" className="overflow-hidden text-[12.5px] leading-[1.5] text-paper">
      <code>{excerpt}</code>
    </pre>
  );
}
