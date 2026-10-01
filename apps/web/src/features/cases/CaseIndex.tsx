import { useMemo, useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { MagnifyingGlass } from "@phosphor-icons/react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { CaseSummary } from "@/lib/api/types";
import { AssessmentStatusWord, StatusWord } from "@/components/Status";
import { EmptyState, ErrorNotice, Skeleton } from "@/components/Feedback";
import { ButtonLink } from "@/components/Button";
import { relativeDay } from "@/lib/format";

type Filter = "all" | "attention" | "compliant" | "open";

const filters: { id: Filter; label: string; test: (c: CaseSummary) => boolean }[] = [
  { id: "all", label: "All", test: () => true },
  {
    id: "attention",
    label: "Needs attention",
    test: (c) =>
      c.run_state === "waiting_for_user" ||
      c.status === "non_compliant" ||
      c.status === "conflicting_policy" ||
      c.status === "insufficient_information",
  },
  { id: "compliant", label: "Compliant within scope", test: (c) => c.status === "compliant_within_scope" },
  { id: "open", label: "In progress", test: (c) => c.run_state !== "completed" },
];

const reviewLabel: Record<CaseSummary["review_state"], string> = {
  unreviewed: "Unreviewed",
  accepted: "Accepted",
  challenged: "Challenged",
  information_requested: "Information requested",
};

export function ResultCell({ c }: { c: CaseSummary }) {
  if (c.run_state === "waiting_for_user") return <StatusWord tone="unknown" label="Waiting for answers" />;
  if (c.run_state === "running" || c.run_state === "queued")
    return <span className="font-semibold">Assessing</span>;
  if (c.run_state === "canceled") return <span className="font-semibold text-ink-2">Canceled</span>;
  if (!c.status) return <span className="text-ink-2">Not assessed</span>;
  return <AssessmentStatusWord status={c.status} />;
}

export function CaseIndex() {
  const q = useQuery({ queryKey: ["cases"], queryFn: () => api.listCases() });
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const rows = useMemo(() => {
    const f = filters.find((x) => x.id === filter)!;
    const term = search.trim().toLowerCase();
    return (q.data ?? []).filter(
      (c) => f.test(c) && (!term || `${c.title} ${c.owner} ${c.business_area}`.toLowerCase().includes(term)),
    );
  }, [q.data, filter, search]);

  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-14">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <h1 className="font-display text-[clamp(2.75rem,5vw,4.5rem)] font-bold leading-none">Cases</h1>
        <div className="relative w-full max-w-sm">
          <label htmlFor="case-search" className="sr-only">
            Search cases
          </label>
          <MagnifyingGlass size={18} aria-hidden className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-2" />
          <input
            id="case-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title, owner or area"
            className="h-12 w-full border-2 border-ink bg-sheet pl-10 pr-3 placeholder:text-ink-2"
          />
        </div>
      </div>

      <div className="mt-8 flex gap-2 overflow-x-auto pb-1" role="group" aria-label="Filter cases">
        {filters.map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={clsx(
              "h-10 shrink-0 border-2 px-4 text-sm font-semibold transition-colors",
              filter === f.id ? "border-ink bg-ink text-paper" : "border-ink/60 hover:border-ink",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {q.isPending ? (
          <div className="space-y-3 border-t-2 border-ink pt-4" aria-busy>
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="grid grid-cols-[minmax(0,1fr)_12rem_8rem] gap-6 py-3">
                <Skeleton className="h-6" />
                <Skeleton className="h-6" />
                <Skeleton className="h-6" />
              </div>
            ))}
          </div>
        ) : q.isError ? (
          <ErrorNotice title="Cases could not be loaded" body="Check your connection and try again." onRetry={() => q.refetch()} />
        ) : rows.length === 0 ? (
          search || filter !== "all" ? (
            <EmptyState
              title="No cases match."
              body={search ? `Nothing matches “${search}” with this filter.` : "No cases match this filter yet."}
            />
          ) : (
            <EmptyState
              title="No cases yet."
              body="Describe a planned activity and Paul.ez will check it against the policy corpus."
              action={<ButtonLink to="/app/cases/new" variant="mark" size="lg">New case</ButtonLink>}
            />
          )
        ) : (
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Cases</caption>
            <thead className="hidden md:table-header-group">
              <tr className="border-b-2 border-ink text-sm">
                <th scope="col" className="py-3 pr-6 font-semibold">Case</th>
                <th scope="col" className="py-3 pr-6 font-semibold">Result</th>
                <th scope="col" className="py-3 pr-6 font-semibold">Open facts</th>
                <th scope="col" className="py-3 pr-6 font-semibold">Review</th>
                <th scope="col" className="py-3 font-semibold">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule border-t-2 border-ink md:border-t-0">
              {rows.map((c) => (
                <tr key={c.id} className="group grid gap-1 py-4 md:table-row md:py-0">
                  <td className="md:py-5 md:pr-6">
                    <Link
                      to={`/app/cases/${c.id}`}
                      className="text-lg font-semibold leading-snug underline-offset-4 group-hover:underline"
                    >
                      {c.title}
                    </Link>
                    <p className="mt-0.5 text-sm text-ink-2">
                      {c.business_area}, {c.owner}
                    </p>
                  </td>
                  <td className="md:py-5 md:pr-6">
                    <ResultCell c={c} />
                  </td>
                  <td className={clsx("tnum md:py-5 md:pr-6", c.unresolved_facts > 0 ? "font-semibold text-unknown" : "text-ink-2")}>
                    <span className="md:hidden">Open facts: </span>
                    {c.unresolved_facts}
                  </td>
                  <td className="text-sm md:py-5 md:pr-6 md:text-base">{reviewLabel[c.review_state]}</td>
                  <td className="tnum text-sm text-ink-2 md:py-5 md:text-base">{relativeDay(c.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
