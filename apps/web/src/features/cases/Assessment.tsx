import { Fragment, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { ArrowRight, CaretDown } from "@phosphor-icons/react";
import clsx from "clsx";
import type { AgentMessage, Assessment, Citation, Fact, Finding } from "@/lib/api/types";
import { RequirementStatusWord, VerdictHeadline } from "@/components/Status";
import { Button } from "@/components/Button";
import { useSectionRef } from "@/features/policies/useSectionRef";

function CitationButtons({
  finding,
  citations,
  onOpen,
}: {
  finding: Finding;
  citations: Map<string, Citation>;
  onOpen: (findingId: string, citationId: string) => void;
}) {
  const citationRef = useSectionRef();
  return (
    <span className="flex flex-wrap justify-end gap-x-3 gap-y-1">
      {finding.citation_ids.map((id) => {
        const c = citations.get(id);
        if (!c) return null;
        return (
          <button
            key={id}
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpen(finding.id, id);
            }}
            className="tnum whitespace-nowrap font-semibold underline decoration-1 underline-offset-4 hover:bg-mark hover:text-on-mark hover:no-underline"
            aria-label={`Open evidence ${citationRef(c)} for ${finding.title}`}
          >
            {citationRef(c)}
          </button>
        );
      })}
    </span>
  );
}

function FindingRow({
  finding,
  index,
  citations,
  facts,
  expanded,
  onToggle,
  onOpen,
}: {
  finding: Finding;
  index: number;
  citations: Map<string, Citation>;
  facts: Map<string, Fact>;
  expanded: boolean;
  onToggle: () => void;
  onOpen: (findingId: string, citationId: string) => void;
}) {
  const reduce = useReducedMotion();
  const panelId = `${finding.id}-detail`;
  return (
    <li className={clsx(finding.status === "not_applicable" && "text-ink-2")}>
      <div className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-x-4 py-4 md:grid-cols-[3rem_minmax(0,1fr)_9rem_auto] md:items-baseline">
        <span className="tnum font-display text-3xl font-bold leading-none">{index + 1}</span>
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={expanded}
          aria-controls={panelId}
          className="group flex items-baseline gap-2 text-left text-lg font-semibold leading-snug"
        >
          {finding.title}
          <CaretDown
            size={16}
            aria-hidden
            className={clsx("shrink-0 translate-y-0.5 transition-transform duration-200", expanded && "rotate-180")}
          />
        </button>
        <span className="col-start-2 mt-1 md:col-start-auto md:mt-0">
          <RequirementStatusWord status={finding.status} />
        </span>
        <span className="col-start-2 mt-1 md:col-start-auto md:mt-0">
          <CitationButtons finding={finding} citations={citations} onOpen={onOpen} />
        </span>
      </div>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={panelId}
            initial={reduce ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduce ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
            className="overflow-hidden"
          >
            <div className="grid gap-5 pb-6 pl-[3.5rem] md:pl-[4rem] lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
              <div>
                <p className="max-w-[60ch] leading-relaxed">{finding.rationale}</p>
                {finding.citation_ids.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={() => onOpen(finding.id, finding.citation_ids[0])}
                    icon={<ArrowRight size={16} aria-hidden />}
                  >
                    Open evidence
                  </Button>
                )}
              </div>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="font-semibold">Facts used</p>
                  <ul className="mt-1 space-y-0.5 text-ink-2">
                    {finding.fact_ids.map((id) => {
                      const f = facts.get(id);
                      return f ? (
                        <li key={id}>
                          {f.label}: {f.value ?? "unknown"}
                        </li>
                      ) : null;
                    })}
                  </ul>
                </div>
                {finding.missing_facts.length > 0 && (
                  <div>
                    <p className="font-semibold text-unknown">Missing</p>
                    <ul className="mt-1 space-y-0.5">
                      {finding.missing_facts.map((m) => (
                        <li key={m}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="text-ink-2">Evidence check: {supportText[finding.support]}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  );
}

const supportText: Record<Finding["support"], string> = {
  validated: "cited text supports this finding",
  unsupported: "not confirmed by the cited text, so it did not decide the result",
  contradicted: "disputed by the validation stage, so it did not decide the result",
  pending: "not checked, so it did not decide the result",
};

const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 } as const;
const severityLabel = { critical: "Critical", high: "High", medium: "Medium", low: "Low" } as const;

function SectionHeading({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h3 id={id} className="font-display text-2xl font-semibold">
      {children}
    </h3>
  );
}

export function AssessmentBody({
  assessment,
  facts,
  onOpenEvidence,
}: {
  assessment: Assessment;
  facts: Fact[];
  onOpenEvidence: (findingId: string, citationId: string) => void;
}) {
  const [open, setOpen] = useState<string | null>(assessment.findings[0]?.id ?? null);
  const citationRef = useSectionRef();
  const citations = new Map(assessment.citations.map((c) => [c.id, c]));
  const factMap = new Map(facts.map((f) => [f.id, f]));
  const findingIndex = new Map(assessment.findings.map((f, i) => [f.id, i + 1]));
  const risks = [...assessment.risks].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  return (
    <div className="space-y-12">
      {assessment.findings.length > 0 && (
        <section aria-labelledby="findings-h">
          <SectionHeading id="findings-h">Findings</SectionHeading>
          <ol className="mt-3 divide-y divide-rule border-y-2 border-ink">
            {assessment.findings.map((f, i) => (
              <FindingRow
                key={f.id}
                finding={f}
                index={i}
                citations={citations}
                facts={factMap}
                expanded={open === f.id}
                onToggle={() => setOpen((o) => (o === f.id ? null : f.id))}
                onOpen={onOpenEvidence}
              />
            ))}
          </ol>
        </section>
      )}

      {risks.length > 0 && (
        <section aria-labelledby="risks-h">
          <SectionHeading id="risks-h">Gaps and risks</SectionHeading>
          <ul className="mt-4 grid gap-x-10 gap-y-6 md:grid-cols-2">
            {risks.map((r) => (
              <li key={r.id}>
                <p className="flex items-baseline gap-3">
                  <span
                    className={clsx(
                      "font-display text-xl font-bold",
                      r.severity === "critical" || r.severity === "high" ? "text-violated" : "text-unknown",
                    )}
                  >
                    {severityLabel[r.severity]}
                  </span>
                  <span className="tnum text-sm text-ink-2">
                    Finding {r.finding_ids.map((id) => findingIndex.get(id)).join(", ")}
                  </span>
                </p>
                <p className="mt-1 max-w-[48ch]">{r.description}</p>
                <p className="mt-1 text-sm text-ink-2">
                  Likelihood {r.likelihood === "unknown" ? "unknown from the facts given" : r.likelihood}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {assessment.recommendations.length > 0 && (
        <section aria-labelledby="actions-h">
          <SectionHeading id="actions-h">Next actions</SectionHeading>
          <ol className="mt-4 space-y-4">
            {assessment.recommendations.map((a) => (
              <li key={a.id} className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-x-4 bg-paper p-4 md:grid-cols-[3rem_minmax(0,1fr)]">
                <span className="tnum pt-0.5 text-sm font-semibold text-ink-2">
                  For {a.finding_ids.map((id) => findingIndex.get(id)).join(", ")}
                </span>
                <div>
                  <p className="text-lg font-semibold leading-snug">{a.action}</p>
                  <p className="mt-2 text-sm text-ink-2">
                    <span className="font-semibold text-ink">{a.suggested_role}</span>
                    {a.kind === "mandatory" ? " • Required by policy" : " • Optional suggestion"}
                  </p>
                  <p className="mt-1 text-sm text-ink-2">Done when: {a.completion_criteria}</p>
                  <p className="mt-2 flex flex-wrap gap-3 text-sm">
                    {a.citation_ids.map((cid) => {
                      const c = citations.get(cid);
                      return c ? (
                        <button
                          key={cid}
                          type="button"
                          className="tnum font-semibold underline decoration-1 underline-offset-4 hover:bg-mark hover:text-on-mark hover:no-underline"
                          onClick={() => onOpenEvidence(a.finding_ids[0], cid)}
                        >
                          {citationRef(c)}
                        </button>
                      ) : null;
                    })}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {assessment.limitations.length > 0 && (
        <section aria-labelledby="limits-h" className="border-t-2 border-ink pt-5">
          <h3 id="limits-h" className="font-semibold">
            Limits of this assessment
          </h3>
          <ul className="mt-2 space-y-1 text-ink-2">
            {assessment.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

export function RequirementTable({
  assessment,
  facts,
  onOpenEvidence,
}: {
  assessment: Assessment;
  facts: Fact[];
  onOpenEvidence: (findingId: string, citationId: string) => void;
}) {
  const citations = new Map(assessment.citations.map((c) => [c.id, c]));
  const factMap = new Map(facts.map((f) => [f.id, f]));
  if (!assessment.findings.length) {
    return <p className="py-10 text-ink-2">No requirements applied to this case.</p>;
  }
  return (
    <div className="-mx-1 overflow-x-auto px-1">
      <table className="w-full min-w-[720px] border-collapse text-left">
        <caption className="sr-only">Requirement matrix</caption>
        <thead>
          <tr className="border-b-2 border-ink text-sm">
            <th scope="col" className="py-3 pr-4 font-semibold">Requirement</th>
            <th scope="col" className="py-3 pr-4 font-semibold">Result</th>
            <th scope="col" className="py-3 pr-4 font-semibold">Known and missing facts</th>
            <th scope="col" className="py-3 font-semibold">Evidence</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule align-top">
          {assessment.findings.map((f) => (
            <tr key={f.id}>
              <th scope="row" className="py-4 pr-4 font-semibold">{f.title}</th>
              <td className="py-4 pr-4">
                <RequirementStatusWord status={f.status} />
              </td>
              <td className="py-4 pr-4 text-sm">
                <ul className="space-y-0.5">
                  {f.fact_ids.map((id) => {
                    const fact = factMap.get(id);
                    return fact ? (
                      <li key={id} className={clsx(fact.value === null && "text-unknown")}>
                        {fact.label}: {fact.value ?? "unknown"}
                      </li>
                    ) : null;
                  })}
                  {f.missing_facts.map((m) => (
                    <li key={m} className="text-unknown">
                      Missing: {m}
                    </li>
                  ))}
                </ul>
              </td>
              <td className="py-4">
                <CitationButtons finding={f} citations={citations} onOpen={onOpenEvidence} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const roleLabel: Record<string, string> = {
  retrieval: "Retrieval",
  analysis: "Analysis",
  risk: "Risk",
  validation: "Validation",
  recommendation: "Recommendation",
  gate: "Final evidence gate",
};

export function RunTimeline({ messages }: { messages: AgentMessage[] }) {
  if (!messages.length) {
    return <p className="py-10 text-ink-2">This run has no recorded agent exchanges.</p>;
  }
  return (
    <div>
      <p className="text-sm text-ink-2">Recorded exchanges from this run, in order.</p>
      <ol className="mt-4 border-l-2 border-ink">
        {messages.map((m, i) => (
          <Fragment key={m.message_id}>
            {/* Times restart when the run is assessed again with clarification answers. */}
            {i > 0 && m.at_ms < messages[i - 1].at_ms && (
              <li className="py-3 pl-6 text-sm font-semibold">Assessed again with your answers</li>
            )}
            <li className="relative grid gap-1 py-3 pl-6 md:grid-cols-[5rem_minmax(0,1fr)] md:gap-4">
              <span aria-hidden className={clsx("absolute -left-[5px] top-[1.15rem] size-2 bg-ink", m.type === "evidence_request" && "bg-mark outline-2 outline-ink")} />
              <span className="tnum text-sm text-ink-2">{(m.at_ms / 1000).toFixed(1)}s</span>
              <div>
                <p className="font-semibold">
                  {roleLabel[m.sender]} <ArrowRight size={14} className="inline -translate-y-px" aria-label="to" />{" "}
                  {roleLabel[m.recipient]}
                </p>
                <p className="text-ink-2">{m.summary}</p>
                {m.type === "evidence_request" && (
                  <p className="mt-1 text-sm font-semibold">Repair loop: validation asked retrieval for more evidence</p>
                )}
              </div>
            </li>
          </Fragment>
        ))}
      </ol>
    </div>
  );
}

const tabTrigger =
  "relative h-12 px-1 font-semibold text-ink-2 outline-none transition-colors hover:text-ink data-[state=active]:text-ink " +
  "after:absolute after:inset-x-0 after:bottom-[-2px] after:h-1 after:bg-mark after:opacity-0 data-[state=active]:after:opacity-100 " +
  "focus-visible:outline-2 focus-visible:outline-ink";

export function AssessmentView({
  assessment,
  facts,
  agentMessages,
  onOpenEvidence,
  reveal,
}: {
  assessment: Assessment;
  facts: Fact[];
  agentMessages: AgentMessage[];
  onOpenEvidence: (findingId: string, citationId: string) => void;
  reveal: boolean;
}) {
  return (
    <div>
      <VerdictHeadline status={assessment.status} reveal={reveal} />
      <p className="mt-3 max-w-[56ch] text-xl leading-snug">{assessment.summary}</p>
      <Tabs.Root defaultValue="assessment" className="mt-8">
        <Tabs.List aria-label="Assessment views" className="flex gap-7 border-b-2 border-ink">
          <Tabs.Trigger value="assessment" className={tabTrigger}>
            Assessment
          </Tabs.Trigger>
          <Tabs.Trigger value="requirements" className={tabTrigger}>
            Requirements
          </Tabs.Trigger>
          <Tabs.Trigger value="trace" className={tabTrigger}>
            Trace
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="assessment" className="pt-8 outline-none">
          <AssessmentBody assessment={assessment} facts={facts} onOpenEvidence={onOpenEvidence} />
        </Tabs.Content>
        <Tabs.Content value="requirements" className="pt-6 outline-none">
          <RequirementTable assessment={assessment} facts={facts} onOpenEvidence={onOpenEvidence} />
        </Tabs.Content>
        <Tabs.Content value="trace" className="pt-6 outline-none">
          <RunTimeline messages={agentMessages} />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
