import { useState } from "react";
import { Link } from "react-router";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight } from "@phosphor-icons/react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { CaseDetail } from "@/lib/api/types";
import type { ReviewInput } from "@/lib/api/client";
import { AssessmentStatusWord, RequirementStatusWord, VerdictHeadline } from "@/components/Status";
import { Button } from "@/components/Button";
import { EmptyState, ErrorNotice, Skeleton } from "@/components/Feedback";

const priority: Record<string, number> = {
  non_compliant: 0,
  conflicting_policy: 1,
  insufficient_information: 2,
  out_of_scope: 3,
  compliant_within_scope: 4,
};

const dispositions: { id: ReviewInput["disposition"]; label: string; help: string }[] = [
  { id: "accepted", label: "Accept", help: "The findings and evidence hold up." },
  { id: "challenged", label: "Challenge", help: "A finding or citation is wrong." },
  { id: "information_requested", label: "Request information", help: "The requester must add facts." },
];

const reviewWord: Record<CaseDetail["review_state"], string> = {
  unreviewed: "Unreviewed",
  accepted: "Accepted",
  challenged: "Challenged",
  information_requested: "Information requested",
};

export function ReviewForm({ detail }: { detail: CaseDetail }) {
  const qc = useQueryClient();
  const [disposition, setDisposition] = useState<ReviewInput["disposition"] | null>(null);
  const [rationale, setRationale] = useState("");
  const [touched, setTouched] = useState(false);
  const save = useMutation({
    mutationFn: () => api.submitReview(detail.id, detail.latest_run_id!, { disposition: disposition!, rationale }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["case", detail.id] });
      void qc.invalidateQueries({ queryKey: ["cases"] });
      setRationale("");
      setDisposition(null);
      setTouched(false);
    },
  });
  const invalid = !disposition || rationale.trim().length < 10;

  return (
    <form
      className="mt-10 border-t-2 border-ink pt-6"
      onSubmit={(e) => {
        e.preventDefault();
        setTouched(true);
        if (!invalid) save.mutate();
      }}
      noValidate
    >
      <fieldset>
        <legend className="font-display text-2xl font-semibold">Your disposition</legend>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          {dispositions.map((d) => (
            <label
              key={d.id}
              className={clsx(
                "cursor-pointer border-2 p-3 transition-colors",
                disposition === d.id ? "border-ink bg-ink text-paper" : "border-ink/60 hover:border-ink",
              )}
            >
              <input
                type="radio"
                name="disposition"
                value={d.id}
                checked={disposition === d.id}
                onChange={() => setDisposition(d.id)}
                className="sr-only"
              />
              <span className="block font-semibold">{d.label}</span>
              <span className="mt-0.5 block text-sm opacity-80">{d.help}</span>
            </label>
          ))}
        </div>
        {touched && !disposition && <p className="mt-2 text-sm font-semibold text-violated">Choose a disposition.</p>}
      </fieldset>
      <div className="mt-6 space-y-2">
        <label htmlFor="rationale" className="font-semibold">
          Rationale
        </label>
        <textarea
          id="rationale"
          rows={3}
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          aria-describedby="rationale-help"
          aria-invalid={touched && rationale.trim().length < 10}
          className="block w-full border-2 border-ink bg-sheet px-3 py-2 placeholder:text-ink-2"
          placeholder="Finding 1 is supported by clause 4.2; approval must be recorded first."
        />
        <p id="rationale-help" className="text-sm text-ink-2">
          Stored with your name and time. The original findings are never overwritten.
        </p>
        {touched && rationale.trim().length < 10 && (
          <p className="text-sm font-semibold text-violated">Write at least a sentence explaining your decision.</p>
        )}
      </div>
      <Button type="submit" className="mt-6" loading={save.isPending}>
        Record review
      </Button>
      {save.isError && (
        <div className="mt-4">
          <ErrorNotice title="The review was not saved" body="Your rationale is still here. Try again." onRetry={() => save.mutate()} />
        </div>
      )}
      {save.isSuccess && <p className="mt-4 font-semibold" role="status">Review recorded.</p>}
    </form>
  );
}

export function ReviewQueue() {
  const list = useQuery({ queryKey: ["cases"], queryFn: () => api.listCases() });
  const candidates = (list.data ?? []).filter((c) => c.run_state === "completed" && c.status);
  const details = useQueries({
    queries: candidates.map((c) => ({ queryKey: ["case", c.id], queryFn: () => api.getCase(c.id) })),
  });
  const queue = details
    .map((d) => d.data)
    .filter((d): d is CaseDetail => Boolean(d?.assessment))
    .sort(
      (a, b) =>
        Number(a.review_state === "accepted") - Number(b.review_state === "accepted") ||
        priority[a.status!] - priority[b.status!],
    );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = queue.find((c) => c.id === selectedId) ?? queue[0];

  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-14">
      <h1 className="font-display text-[clamp(2.75rem,5vw,4.5rem)] font-bold leading-none">Reviews</h1>
      <p className="mt-4 max-w-[60ch] text-lg text-ink-2">
        Violations and conflicts come first. A review records a person&rsquo;s decision; it does not approve the business
        activity itself.
      </p>

      {list.isPending || details.some((d) => d.isPending) ? (
        <div className="mt-10 grid gap-10 lg:grid-cols-[24rem_minmax(0,1fr)]" aria-busy>
          <Skeleton className="h-72" />
          <Skeleton className="h-96" />
        </div>
      ) : queue.length === 0 ? (
        <EmptyState title="Nothing to review." body="Completed assessments appear here for a reviewer's decision." />
      ) : (
        <div className="mt-10 grid gap-x-12 gap-y-10 lg:grid-cols-[24rem_minmax(0,1fr)]">
          <ol className="divide-y divide-rule border-y-2 border-ink lg:self-start" aria-label="Review queue">
            {queue.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  aria-current={selected?.id === c.id}
                  onClick={() => setSelectedId(c.id)}
                  className={clsx(
                    "w-full px-3 py-4 text-left transition-colors",
                    selected?.id === c.id ? "bg-ink text-paper" : "hover:bg-sheet",
                  )}
                >
                  <span className="block font-semibold leading-snug">{c.title}</span>
                  <span className="mt-1 flex flex-wrap items-baseline gap-x-3 text-sm">
                    {selected?.id === c.id ? (
                      <span className="font-semibold">{c.assessment && reviewWord[c.review_state]}</span>
                    ) : (
                      <>
                        <AssessmentStatusWord status={c.assessment!.status} />
                        <span className="text-ink-2">{reviewWord[c.review_state]}</span>
                      </>
                    )}
                  </span>
                </button>
              </li>
            ))}
          </ol>

          {selected?.assessment && (
            <section aria-label={`Review ${selected.title}`} className="min-w-0 bg-sheet p-6 md:p-10">
              <VerdictHeadline status={selected.assessment.status} size="md" reveal={false} as="p" />
              <p className="mt-2 font-semibold">{selected.title}</p>
              <p className="mt-3 max-w-[58ch] text-lg">{selected.assessment.summary}</p>
              <ul className="mt-6 divide-y divide-rule border-y-2 border-ink">
                {selected.assessment.findings.map((f, i) => (
                  <li key={f.id} className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-baseline gap-4 py-3">
                    <span className="tnum font-display text-xl font-bold">{i + 1}</span>
                    <span className="font-medium">{f.title}</span>
                    <RequirementStatusWord status={f.status} />
                  </li>
                ))}
              </ul>
              <Link
                to={`/app/cases/${selected.id}`}
                className="mt-4 inline-flex items-center gap-1.5 font-semibold underline decoration-1 underline-offset-4"
              >
                Open the case and its evidence <ArrowRight size={16} aria-hidden />
              </Link>
              <p className="mt-6 text-sm">
                Current review state: <span className="font-semibold">{reviewWord[selected.review_state]}</span>
              </p>
              <ReviewForm key={selected.id} detail={selected} />
            </section>
          )}
        </div>
      )}
    </div>
  );
}
