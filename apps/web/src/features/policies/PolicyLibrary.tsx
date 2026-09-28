import { useMemo, useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { Policy } from "@/lib/api/types";
import { EmptyState, ErrorNotice, Skeleton } from "@/components/Feedback";
import { formatDate, todayIso } from "@/lib/format";

function activeVersion(p: Policy) {
  return p.versions.find((v) => v.id === p.active_version_id) ?? p.versions[0];
}

function IndexStatus({ p }: { p: Policy }) {
  const draft = p.versions.find((v) => v.status === "draft");
  const failed = p.versions.find((v) => v.index_status === "failed");
  if (failed) return <span className="font-semibold text-violated">Indexing failed</span>;
  if (draft?.index_status === "indexing")
    return (
      <span>
        <span className="font-semibold">Ready</span>
        <span className="block text-sm text-ink-2">Draft {draft.label} indexing</span>
      </span>
    );
  return <span className="font-semibold">Ready</span>;
}

export function PolicyLibrary() {
  const q = useQuery({ queryKey: ["policies"], queryFn: () => api.listPolicies() });
  const [category, setCategory] = useState<string>("All");
  const categories = useMemo(
    () => ["All", ...new Set((q.data ?? []).map((p) => p.category))].sort((a, b) => (a === "All" ? -1 : b === "All" ? 1 : a.localeCompare(b))),
    [q.data],
  );
  const rows = (q.data ?? []).filter((p) => category === "All" || p.category === category);
  const today = todayIso();

  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-14">
      <h1 className="font-display text-[clamp(2.75rem,5vw,4.5rem)] font-bold leading-none">Policies</h1>
      <p className="mt-4 max-w-[60ch] text-lg text-ink-2">
        The fictional Kestrel Mutual corpus Clause searches. Every finding cites a clause in one of these versions.
      </p>

      <h2 className="mt-12 font-display text-3xl font-semibold">All policies</h2>
      <div className="mt-5 flex gap-2 overflow-x-auto pb-1" role="group" aria-label="Filter by category">
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            aria-pressed={category === c}
            onClick={() => setCategory(c)}
            className={clsx(
              "h-10 shrink-0 border-2 px-4 text-sm font-semibold transition-colors",
              category === c ? "border-ink bg-ink text-paper" : "border-ink/60 hover:border-ink",
            )}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {q.isPending ? (
          <div className="space-y-4 border-t-2 border-ink pt-4" aria-busy>
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : q.isError ? (
          <ErrorNotice title="Policies could not be loaded" body="Try again in a moment." onRetry={() => q.refetch()} />
        ) : rows.length === 0 ? (
          <EmptyState title="No policies here." body="No policy in the corpus has this category." />
        ) : (
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Policies</caption>
            <thead className="hidden md:table-header-group">
              <tr className="border-b-2 border-ink text-sm">
                <th scope="col" className="py-3 pr-6 font-semibold">Policy</th>
                <th scope="col" className="py-3 pr-6 font-semibold">Category</th>
                <th scope="col" className="py-3 pr-6 font-semibold">In force</th>
                <th scope="col" className="py-3 font-semibold">Search index</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule border-t-2 border-ink md:border-t-0">
              {rows.map((p) => {
                const v = activeVersion(p);
                const next = p.versions.find((x) => x.status === "published" && x.effective_from > today);
                return (
                  <tr key={p.id} className="group grid gap-1 py-4 md:table-row md:py-0">
                    <td className="md:py-5 md:pr-6">
                      <Link
                        to={`/app/policies/${p.id}/versions/${v.id}`}
                        className="text-lg font-semibold underline-offset-4 group-hover:underline"
                      >
                        {p.title}
                      </Link>
                      <p className="mt-0.5 text-sm text-ink-2">
                        {p.business_area}, owned by {p.owner}
                      </p>
                    </td>
                    <td className="text-sm md:py-5 md:pr-6 md:text-base">{p.category}</td>
                    <td className="tnum md:py-5 md:pr-6">
                      <span className="font-semibold">{v.label}</span>
                      <span className="text-ink-2"> since {formatDate(v.effective_from)}</span>
                      {next && (
                        <span className="block text-sm">
                          <span className="mark-span font-semibold">{next.label}</span> from {formatDate(next.effective_from)}
                        </span>
                      )}
                    </td>
                    <td className="md:py-5">
                      <IndexStatus p={p} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
