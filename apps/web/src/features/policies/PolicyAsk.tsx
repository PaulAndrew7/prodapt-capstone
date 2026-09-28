import { useState } from "react";
import { Link } from "react-router";
import { useMutation, useQueries } from "@tanstack/react-query";
import { ArrowUpRight, MagnifyingGlass } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import type { LookupAnswer } from "@/lib/api/types";
import { Button } from "@/components/Button";
import { ErrorNotice, Skeleton } from "@/components/Feedback";
import { MarkedText } from "@/components/HighlightMark";

/* F06 grounded lookup: a short answer, then the exact clauses that support it. */
export function LookupAnswerView({ answer, play = true }: { answer: LookupAnswer; play?: boolean }) {
  const versionIds = [...new Set(answer.citations.map((c) => c.policy_version_id))];
  const versions = useQueries({
    queries: versionIds.map((id) => ({
      queryKey: ["policy-version", id],
      queryFn: () => api.getPolicyVersion(id),
      staleTime: Infinity,
    })),
  });
  const byId = new Map(versions.filter((q) => q.data).map((q) => [q.data!.id, q.data!]));
  return (
    <div>
      <p className="max-w-[60ch] text-xl leading-snug">{answer.answer}</p>
      <p className="mt-2 text-sm text-ink-2">
        {answer.support === "validated"
          ? "Each quote below was matched to the stored policy text. Read the clauses to confirm the answer."
          : answer.citations.length
            ? "Some citations could not be matched to the policy text; treat this answer with care."
            : "No policy text supports an answer to this question."}{" "}
        <span className="tnum">Snapshot {answer.snapshot_id}.</span>
      </p>
      <ol className="mt-6 grid gap-6 md:grid-cols-2">
        {answer.citations.map((c, i) => {
          const v = byId.get(c.policy_version_id);
          const query = versions[versionIds.indexOf(c.policy_version_id)];
          const clause = v?.clauses.find((x) => x.id === c.clause_id);
          const number = c.section_path[c.section_path.length - 1];
          return (
            <li key={c.id} className="bg-sheet p-5">
              {query.isError ? (
                <ErrorNotice
                  title="This citation could not be loaded"
                  body="Retry to read the policy text behind this answer."
                  onRetry={() => query.refetch()}
                />
              ) : !v ? (
                <Skeleton className="h-28" />
              ) : !clause ? (
                <div role="status">
                  <p>This clause is missing from the policy version. The saved quote could not be checked against the current source.</p>
                  <blockquote className="mt-3">{c.quote}</blockquote>
                  <Link to={`/app/policies/${v.policy_id}/versions/${v.id}`} className="mt-3 inline-block underline">Open policy version</Link>
                </div>
              ) : (
                <>
                  <p className="text-sm font-semibold">{v.policy_title}</p>
                  <p className="tnum text-sm text-ink-2">
                    {v.label}, page {c.page_index + 1}
                  </p>
                  <p className="mt-3 flex items-baseline gap-3">
                    <span className="tnum font-display text-4xl font-bold leading-none">{number}</span>
                    <span className="font-semibold">{clause.heading}</span>
                  </p>
                  <p className="mt-3 leading-relaxed">
                    <MarkedText text={clause.text} quote={c.quote} play={play} delay={0.3 + i * 0.15} />
                  </p>
                  <Link
                    to={`/app/policies/${v.policy_id}/versions/${v.id}?clause=${encodeURIComponent(c.clause_id)}&q=${encodeURIComponent(c.quote)}`}
                    className="mt-3 inline-flex items-center gap-1 text-sm font-semibold underline decoration-1 underline-offset-4"
                  >
                    Open in policy <ArrowUpRight size={14} aria-hidden />
                  </Link>
                </>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export { LOOKUP_QUESTION as LOOKUP_EXAMPLE } from "@/fixtures/lookup";
import { LOOKUP_QUESTION as LOOKUP_EXAMPLE } from "@/fixtures/lookup";

export function PolicyAsk() {
  const [q, setQ] = useState("");
  const ask = useMutation({ mutationFn: (question: string) => api.lookup(question) });
  return (
    <section aria-labelledby="ask-h" className="border-y-2 border-ink py-8">
      <h2 id="ask-h" className="font-display text-3xl font-semibold">
        Ask a policy question
      </h2>
      <form
        className="mt-4 flex flex-col gap-3 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          if (!ask.isPending && q.trim().length >= 2 && q.trim().length <= 2000) ask.mutate(q.trim());
        }}
      >
        <label htmlFor="ask" className="sr-only">
          Policy question
        </label>
        <div className="relative flex-1">
          <MagnifyingGlass size={18} aria-hidden className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-2" />
          <input
            id="ask"
            maxLength={2000}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={LOOKUP_EXAMPLE}
            className="h-12 w-full border-2 border-ink bg-sheet pl-10 pr-3 placeholder:text-ink-2"
          />
        </div>
        <Button type="submit" size="lg" className="h-12" loading={ask.isPending} disabled={q.trim().length < 2}>
          Ask
        </Button>
      </form>
      {!q && !ask.data && (
        <button type="button" className="mt-3 text-sm font-semibold underline decoration-1 underline-offset-4" onClick={() => setQ(LOOKUP_EXAMPLE)}>
          Use the example question
        </button>
      )}
      <div className="mt-8" aria-live="polite">
        {ask.isPending && (
          <div className="space-y-3">
            <Skeleton className="h-6 w-4/5" />
            <Skeleton className="h-6 w-3/5" />
            <div className="grid gap-6 pt-4 md:grid-cols-2">
              <Skeleton className="h-40" />
              <Skeleton className="h-40" />
            </div>
          </div>
        )}
        {ask.isError && <ErrorNotice title="No answer this time" body={ask.error.message} onRetry={() => ask.mutate(ask.variables!)} />}
        {ask.data && <LookupAnswerView answer={ask.data} />}
      </div>
    </section>
  );
}
