import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight } from "@phosphor-icons/react";
import type { Assessment } from "@/lib/api/types";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { ErrorNotice, Skeleton } from "@/components/Feedback";
import { RequirementStatusWord, VerdictHeadline } from "@/components/Status";
import { HighlightMark } from "@/components/HighlightMark";
import { vendorHypotheticalChanges } from "@/fixtures/vendorCase";

/*
  F19: a separate branch with explicitly changed facts. The real case is never edited,
  and every surface of the result says "Hypothetical".
*/
export function HypotheticalPanel({
  caseId,
  real,
  onBack,
}: {
  caseId: string;
  real: Assessment;
  onBack: () => void;
}) {
  const changes = vendorHypotheticalChanges;
  const run = useMutation({
    mutationFn: () =>
      api.createBranch(
        caseId,
        changes.map((c) => ({ fact_key: c.label, value: c.to })),
      ),
  });
  const result = run.data;

  return (
    <div>
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 font-semibold underline decoration-1 underline-offset-4"
      >
        <ArrowLeft size={16} aria-hidden /> Back to the real case
      </button>

      <h2 className="mt-6 font-display text-[clamp(2.25rem,3.6vw,3.5rem)] font-bold leading-[1.05]">
        What would change the answer?
      </h2>
      <p className="mt-3 max-w-[58ch] text-lg text-ink-2">
        This runs a separate hypothetical branch with the facts below changed. The real case and its result stay as
        they are.
      </p>

      <ul className="mt-8 divide-y divide-rule border-y-2 border-ink">
        {changes.map((c) => (
          <li key={c.label} className="grid gap-1 py-4 sm:grid-cols-[12rem_minmax(0,1fr)] sm:items-baseline sm:gap-4">
            <span className="font-semibold">{c.label}</span>
            <span className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <s className="text-ink-2 decoration-violated decoration-2">{c.from}</s>
              <ArrowRight size={16} aria-label="becomes" className="translate-y-0.5" />
              <HighlightMark play={Boolean(result)}>{c.to}</HighlightMark>
            </span>
          </li>
        ))}
      </ul>

      {!result && (
        <Button className="mt-8" variant="mark" size="lg" loading={run.isPending} onClick={() => run.mutate()}>
          Run hypothetical
        </Button>
      )}
      {run.isPending && (
        <div className="mt-10 grid gap-8 md:grid-cols-2" aria-live="polite">
          <p className="sr-only">Running the hypothetical branch</p>
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      )}
      {run.isError && (
        <div className="mt-8">
          <ErrorNotice
            title="The hypothetical did not run"
            body="Nothing changed in the real case. Try again."
            onRetry={() => run.mutate()}
          />
        </div>
      )}

      {result && <Comparison real={real} hypothetical={result} />}
    </div>
  );
}

function Comparison({ real, hypothetical }: { real: Assessment; hypothetical: Assessment }) {
  const after = new Map(hypothetical.findings.map((f) => [f.id, f]));
  return (
    <section aria-label="Comparison" className="mt-12">
      <div className="grid gap-10 md:grid-cols-2">
        <div>
          <VerdictHeadline status={real.status} size="md" reveal={false} as="p" />
          <p className="mt-2 font-semibold text-ink-2">Real case</p>
        </div>
        <div>
          <VerdictHeadline status={hypothetical.status} size="md" as="p" />
          <p className="mt-2 font-semibold">
            <HighlightMark>Hypothetical</HighlightMark>
          </p>
        </div>
      </div>
      <p className="mt-4 max-w-[60ch]">{hypothetical.summary}</p>

      <table className="mt-8 w-full border-collapse text-left">
        <caption className="sr-only">Finding changes</caption>
        <thead>
          <tr className="border-b-2 border-ink text-sm">
            <th scope="col" className="py-3 pr-4 font-semibold">Requirement</th>
            <th scope="col" className="py-3 pr-4 font-semibold">Real case</th>
            <th scope="col" className="py-3 font-semibold">Hypothetical</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {real.findings.map((f) => {
            const h = after.get(f.id);
            return (
              <tr key={f.id}>
                <th scope="row" className="py-3 pr-4 font-medium">{f.title}</th>
                <td className="py-3 pr-4"><RequirementStatusWord status={f.status} /></td>
                <td className="py-3">{h ? <RequirementStatusWord status={h.status} /> : "Not assessed"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ul className="mt-6 space-y-1 text-sm text-ink-2">
        {hypothetical.limitations.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
    </section>
  );
}
