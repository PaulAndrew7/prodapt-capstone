import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { ScenarioComposer } from "@/features/cases/ScenarioComposer";
import { ResultCell } from "@/features/cases/CaseIndex";
import { Skeleton } from "@/components/Feedback";
import { formatDate, relativeDay, todayIso } from "@/lib/format";

export function Overview() {
  const cases = useQuery({ queryKey: ["cases"], queryFn: () => api.listCases() });
  const policies = useQuery({ queryKey: ["policies"], queryFn: () => api.listPolicies() });

  const today = todayIso();
  const versions = policies.data?.flatMap((p) => p.versions.map((v) => ({ ...v, policy: p }))) ?? [];
  const upcoming = versions
    .filter((v) => v.status === "published" && v.effective_from > today)
    .sort((a, b) => a.effective_from.localeCompare(b.effective_from));
  const drafts = versions.filter((v) => v.status === "draft");
  const waiting = cases.data?.filter((c) => c.run_state === "waiting_for_user") ?? [];

  return (
    <div className="mx-auto max-w-[1600px] px-4 md:px-8">
      <section className="py-10 md:py-14">
        <ScenarioComposer />
      </section>

      <div className="grid gap-x-16 gap-y-14 border-t-2 border-ink py-12 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section aria-labelledby="recent-h">
          <div className="flex items-baseline justify-between gap-4">
            <h2 id="recent-h" className="font-display text-3xl font-semibold">
              Recent cases
            </h2>
            <Link to="/app/cases" className="inline-flex items-center gap-1 font-semibold underline decoration-1 underline-offset-4">
              All cases <ArrowRight size={16} aria-hidden />
            </Link>
          </div>
          <ul className="mt-4 divide-y divide-rule border-y-2 border-ink">
            {cases.isPending
              ? [0, 1, 2].map((i) => (
                  <li key={i} className="py-4">
                    <Skeleton className="h-6 w-3/4" />
                  </li>
                ))
              : cases.data?.slice(0, 5).map((c) => (
                  <li key={c.id} className="grid gap-1 py-4 sm:grid-cols-[minmax(0,1fr)_14rem_7rem] sm:items-baseline sm:gap-6">
                    <Link to={`/app/cases/${c.id}`} className="font-semibold leading-snug underline-offset-4 hover:underline">
                      {c.title}
                    </Link>
                    <ResultCell c={c} />
                    <span className="tnum text-sm text-ink-2">{relativeDay(c.updated_at)}</span>
                  </li>
                ))}
          </ul>
          {waiting.length > 0 && (
            <p className="mt-4 text-ink-2">
              {waiting.length === 1 ? "One case is" : `${waiting.length} cases are`} waiting for your answers.
            </p>
          )}
        </section>

        <section aria-labelledby="corpus-h">
          <div className="flex items-baseline justify-between gap-4">
            <h2 id="corpus-h" className="font-display text-3xl font-semibold">
              Policy corpus
            </h2>
            <Link to="/app/policies" className="inline-flex items-center gap-1 font-semibold underline decoration-1 underline-offset-4">
              Policies <ArrowRight size={16} aria-hidden />
            </Link>
          </div>
          {policies.isPending ? (
            <Skeleton className="mt-4 h-32" />
          ) : (
            <dl className="mt-4 divide-y divide-rule border-y-2 border-ink">
              <div className="flex items-baseline justify-between py-3">
                <dt>Published policies</dt>
                <dd className="tnum font-semibold">{policies.data?.length ?? 0}</dd>
              </div>
              <div className="flex items-baseline justify-between py-3">
                <dt>Drafts being indexed</dt>
                <dd className="tnum font-semibold">{drafts.length}</dd>
              </div>
              <div className="py-3">
                <dt>Coming into force</dt>
                {upcoming.length ? (
                  upcoming.map((v) => (
                    <dd key={v.id} className="mt-1">
                      <Link
                        to={`/app/policies/${v.policy.id}/versions/${v.id}`}
                        className="font-semibold underline decoration-1 underline-offset-4"
                      >
                        {v.policy.title} {v.label}
                      </Link>
                      <span className="tnum text-ink-2">, from {formatDate(v.effective_from)}</span>
                    </dd>
                  ))
                ) : (
                  <dd className="mt-1 text-ink-2">No scheduled changes.</dd>
                )}
              </div>
            </dl>
          )}
          <p className="mt-4 text-sm text-ink-2">
            Kestrel Mutual is a fictional organization. Its policies are demo material, not law or regulatory guidance.
          </p>
        </section>
      </div>
    </div>
  );
}
