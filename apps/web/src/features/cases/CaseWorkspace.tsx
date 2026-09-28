import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence } from "motion/react";
import { DownloadSimple, Flask, Stop } from "@phosphor-icons/react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { CaseDetail, Clause } from "@/lib/api/types";
import { Button } from "@/components/Button";
import { EmptyState, ErrorNotice, Skeleton } from "@/components/Feedback";
import { StageTrack } from "@/components/StageTrack";
import { AssessmentStatusWord } from "@/components/Status";
import { formatDate } from "@/lib/format";
import { useCaseRun } from "./useCaseRun";
import { ClarificationBlock, Composer, FactList, Transcript } from "./Conversation";
import { AssessmentView } from "./Assessment";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { HypotheticalPanel } from "./Hypothetical";
import { exportReport } from "@/lib/exportReport";
import { PrintReport } from "./PrintReport";
import { STAGES } from "@/lib/events/runStore";
import { AvatarPanel } from "@/features/avatar/AvatarPanel";

type Evidence = { findingId: string; citationId: string } | null;

export function CaseHeader({
  detail,
  phase,
  onHypothetical,
  hypotheticalOpen,
  onCancel,
  canceling,
}: {
  detail: CaseDetail;
  phase: string;
  onHypothetical: () => void;
  hypotheticalOpen: boolean;
  onCancel: () => void;
  canceling: boolean;
}) {
  const running = phase === "queued" || phase === "running" || phase === "waiting_for_user";
  const facts: [string, string][] = [
    ["Business area", detail.business_area],
    ["Scope", detail.scope],
    ["As of", formatDate(detail.as_of)],
    ["Policy snapshot", detail.policy_snapshot_id],
  ];
  return (
    <div className="border-b-2 border-ink px-4 py-6 md:px-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between md:gap-8">
        <div className="min-w-0 flex-1">
          <h1 className="max-w-[28ch] font-display text-[clamp(1.75rem,2.6vw,2.5rem)] font-semibold leading-[1.1]">
            {detail.title}
          </h1>
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:flex sm:flex-wrap sm:gap-x-8 sm:gap-y-2">
            {facts.map(([k, v]) => (
              <div key={k}>
                <dt className="text-ink-2">{k}</dt>
                <dd className="tnum font-semibold">{v}</dd>
              </div>
            ))}
            <div>
              <dt className="text-ink-2">Result</dt>
              <dd>
                {detail.assessment && phase === "completed" ? (
                  <AssessmentStatusWord status={detail.assessment.status} />
                ) : (
                  <span className="font-semibold">{running ? "Assessing" : phase === "canceled" ? "Canceled" : "Not assessed"}</span>
                )}
              </dd>
            </div>
          </dl>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {running && (
            <Button variant="outline" size="sm" onClick={onCancel} loading={canceling} icon={<Stop size={16} aria-hidden />}>
              Cancel run
            </Button>
          )}
          {api.mode === "fixture" && detail.assessment && phase === "completed" && detail.assessment.status === "non_compliant" && !hypotheticalOpen && detail.facts.some((f) => f.key === "data_owner_approval") && (
            <Button variant="outline" size="sm" onClick={onHypothetical} icon={<Flask size={16} aria-hidden />}>
              Try a hypothetical
            </Button>
          )}
          {detail.assessment && phase === "completed" && (
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              Print report
            </Button>
          )}
          {detail.assessment && phase === "completed" && (
            <Button variant="ghost" size="sm" onClick={() => exportReport(detail)} icon={<DownloadSimple size={16} aria-hidden />}>
              Export report
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export function CaseWorkspace() {
  const { caseId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const qc = useQueryClient();
  const query = useQuery({ queryKey: ["case", caseId], queryFn: () => api.getCase(caseId), enabled: Boolean(caseId) });
  const detail = query.data;
  const { phase, stages, events } = useCaseRun(detail);
  const [evidence, setEvidence] = useState<Evidence>(null);
  const [hypothetical, setHypothetical] = useState(false);
  const [pane, setPane] = useState<"conversation" | "assessment">("conversation");
  const [composerFocused, setComposerFocused] = useState(false);
  const [ackKey, setAckKey] = useState(0);
  const lastTrigger = useRef<HTMLElement | null>(null);
  const [revealKey, setRevealKey] = useState<string | null>(null);

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["case", caseId] });
    void qc.invalidateQueries({ queryKey: ["cases"] });
  };

  const start = useMutation({ mutationFn: () => api.startRun(caseId), onSuccess: refresh });
  const answer = useMutation({
    mutationFn: (answers: Record<string, string | null>) => api.answerClarification(detail!.latest_run_id!, answers),
    onSuccess: refresh,
  });
  const cancel = useMutation({ mutationFn: () => api.cancelRun(detail!.latest_run_id!), onSuccess: refresh });

  // A case created from the New case screen starts its run once, then drops the flag.
  const autostarted = useRef(false);
  useEffect(() => {
    if (params.get("run") === "start" && detail && !detail.latest_run_id && !autostarted.current) {
      autostarted.current = true;
      start.mutate();
      params.delete("run");
      setParams(params, { replace: true });
    }
  }, [params, detail, setParams, start]);

  // Verdict words animate only when a result arrives in this session, not on every visit.
  useEffect(() => {
    if (phase === "running" || phase === "queued") setRevealKey("pending");
    if (phase === "completed" && revealKey === "pending") {
      setRevealKey("reveal");
      setPane("assessment");
    }
  }, [phase, revealKey]);

  const openEvidence = useCallback((findingId: string, citationId: string) => {
    lastTrigger.current = document.activeElement as HTMLElement | null;
    setEvidence({ findingId, citationId });
  }, []);
  const closeEvidence = useCallback(() => {
    setEvidence(null);
    requestAnimationFrame(() => lastTrigger.current?.focus());
  }, []);

  const [previewClause, setPreviewClause] = useState<Clause | null>(null);
  const openClause = (clause: Clause) => {
    lastTrigger.current = document.activeElement as HTMLElement | null;
    setPreviewClause(clause);
  };

  if (query.isPending) {
    return (
      <div className="px-4 py-10 md:px-8" aria-busy>
        <Skeleton className="h-10 w-2/3 max-w-xl" />
        <Skeleton className="mt-4 h-5 w-1/2 max-w-md" />
        <div className="mt-10 grid gap-10 lg:grid-cols-[38fr_62fr]">
          <Skeleton className="h-80" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }
  if (query.isError || !detail) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 md:px-8">
        <ErrorNotice title="This case could not be loaded" body="It may not exist, or you may not have access to it." onRetry={() => query.refetch()} />
      </div>
    );
  }

  const assessment = detail.assessment;
  const activeFinding = evidence && assessment?.findings.find((f) => f.id === evidence.findingId);
  const failure = [...events].reverse().find((e) => e.type === "run.failed")?.payload.message;
  const running = phase === "queued" || phase === "running";
  const waiting = phase === "waiting_for_user";

  return (
    <div className="mx-auto flex max-w-[1600px] flex-col lg:h-[calc(100dvh-4rem)]">
      {detail.assessment && phase === "completed" && <PrintReport detail={detail} />}
      <CaseHeader
        detail={detail}
        phase={phase}
        onHypothetical={() => {
          setHypothetical(true);
          setPane("assessment");
        }}
        hypotheticalOpen={hypothetical}
        onCancel={() => cancel.mutate()}
        canceling={cancel.isPending}
      />

      <div className="flex border-b-2 border-ink lg:hidden" role="tablist" aria-label="Workspace panes">
        {(["conversation", "assessment"] as const).map((p) => (
          <button
            key={p}
            role="tab"
            aria-selected={pane === p}
            onClick={() => setPane(p)}
            className={clsx(
              "relative h-12 flex-1 font-semibold capitalize",
              pane === p ? "text-ink after:absolute after:inset-x-0 after:bottom-[-2px] after:h-1 after:bg-mark" : "text-ink-2",
            )}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="grid lg:min-h-0 lg:flex-1 lg:grid-cols-[minmax(0,38fr)_minmax(0,62fr)]">
        <section
          aria-label="Conversation and facts"
          className={clsx("min-h-0 flex-col lg:flex lg:border-r-2 lg:border-ink", pane === "conversation" ? "flex" : "hidden")}
        >
          <div tabIndex={0} aria-label="Conversation, questions and facts" role="region" className="flex-1 space-y-10 px-4 py-8 outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ink md:px-8 lg:overflow-y-auto lg:overscroll-contain">
            <Transcript messages={detail.messages} />
            {waiting && detail.pending_questions.length > 0 && (
              <ClarificationBlock
                questions={detail.pending_questions}
                onSubmit={(a) => answer.mutate(a)}
                submitting={answer.isPending}
                onOpenClause={openClause}
              />
            )}
            {answer.isError && (
              <ErrorNotice title="Your answers did not send" body="They are still filled in. Try again." onRetry={() => answer.reset()} />
            )}
            <FactList facts={detail.facts} />
            {phase === "completed" && (
              <Button variant="outline" className="lg:hidden" onClick={() => setPane("assessment")}>
                View assessment
              </Button>
            )}
          </div>
          <div className="hidden lg:block">
            <AvatarPanel
              phase={phase}
              composerFocused={composerFocused}
              evidenceOpen={Boolean(evidence || previewClause)}
              ackKey={ackKey}
              stageLabel={STAGES.find((s) => stages[s.role] === "active")?.label ?? null}
            />
          </div>
          <div className={clsx("sticky bottom-0 lg:static", waiting && "hidden")}>
            <Composer
              onFocusChange={setComposerFocused}
              disabled={running || waiting}
              sending={start.isPending}
              hint={
                running
                  ? "Available when this run finishes."
                  : waiting
                    ? "Answer the questions above first."
                    : detail.latest_run_id
                      ? "A follow-up starts a new run. The current result stays in history."
                      : "Press Ctrl+Enter to send."
              }
              onSend={async (text) => {
                await api.addMessage(caseId, text);
                setAckKey((k) => k + 1);
                await start.mutateAsync();
              }}
            />
          </div>
        </section>

        <section
          aria-label="Assessment"
          className={clsx("relative min-h-0 overflow-hidden bg-sheet lg:block", pane === "assessment" ? "block" : "hidden")}
        >
          <div tabIndex={0} aria-label="Assessment details" role="region" className="px-4 py-8 outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ink md:px-10 md:py-10 lg:h-full lg:overflow-y-auto lg:overscroll-contain">
            {hypothetical && assessment ? (
              <HypotheticalPanel caseId={detail.id} real={assessment} onBack={() => setHypothetical(false)} />
            ) : (
              <>
                {(running || waiting) && (
                  <div className="space-y-10">
                    <StageTrack stages={stages} />
                    {waiting ? (
                      <div>
                        <p className="font-display text-[clamp(2rem,3.2vw,3rem)] font-bold leading-[1.05]">
                          Waiting for your answers.
                        </p>
                        <p className="mt-3 max-w-[52ch] text-lg text-ink-2">
                          Retrieval and a first analysis are done. Answer the questions in the conversation, or say
                          you don&rsquo;t know, to finish the assessment.
                        </p>
                      </div>
                    ) : (
                      <div aria-hidden className="space-y-6">
                        <Skeleton className="h-16 w-3/5" />
                        <Skeleton className="h-5 w-4/5" />
                        <div className="space-y-4 pt-6">
                          {[0, 1, 2].map((i) => (
                            <div key={i} className="grid grid-cols-[3rem_1fr_8rem] gap-4">
                              <Skeleton className="h-8" />
                              <Skeleton className="h-6" />
                              <Skeleton className="h-6" />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {phase === "completed" && assessment && (
                  <AssessmentView
                    assessment={assessment}
                    facts={detail.facts}
                    agentMessages={detail.agent_messages}
                    onOpenEvidence={openEvidence}
                    reveal={revealKey === "reveal"}
                  />
                )}
                {phase === "idle" && (
                  <EmptyState
                    title="Not assessed yet."
                    body="Clause will retrieve the relevant clauses, ask about anything that decides the result, and pin each finding to its source."
                    action={
                      <Button variant="mark" size="lg" loading={start.isPending} onClick={() => start.mutate()}>
                        Assess
                      </Button>
                    }
                  />
                )}
                {phase === "canceled" && (
                  <EmptyState
                    title="Run canceled."
                    body="No result was recorded for this run. Start a new one when you are ready."
                    action={
                      <Button variant="primary" loading={start.isPending} onClick={() => start.mutate()}>
                        Assess
                      </Button>
                    }
                  />
                )}
                {phase === "failed" && (
                  <ErrorNotice
                    title="The run failed before a result"
                    body={`${typeof failure === "string" ? `${failure} ` : ""}A failed run is not a compliance verdict. Start a new run; nothing was recorded as a result.`}
                    onRetry={() => start.mutate()}
                  />
                )}
                {start.isError && (
                  <div className="mt-6">
                    <ErrorNotice
                      title="The assessment did not start"
                      body={start.error.message}
                      onRetry={() => start.mutate()}
                    />
                  </div>
                )}
              </>
            )}
          </div>

          <AnimatePresence>
            {evidence && activeFinding && assessment && (
              <EvidenceDrawer
                key={evidence.findingId}
                title={activeFinding.title}
                status={activeFinding.status}
                citations={assessment.citations.filter((c) => activeFinding.citation_ids.includes(c.id))}
                focusCitationId={evidence.citationId}
                onClose={closeEvidence}
              />
            )}
            {previewClause && (
              <EvidenceDrawer
                key={`preview-${previewClause.id}`}
                title={previewClause.heading}
                citations={[
                  {
                    id: "preview",
                    policy_version_id: previewClause.policy_version_id,
                    clause_id: previewClause.id,
                    page_index: previewClause.page_index,
                    section_path: previewClause.section_path,
                    quote: "",
                    source_url: "",
                  },
                ]}
                focusCitationId="preview"
                onClose={() => {
                  setPreviewClause(null);
                  requestAnimationFrame(() => lastTrigger.current?.focus());
                }}
              />
            )}
          </AnimatePresence>
        </section>
      </div>
    </div>
  );
}
