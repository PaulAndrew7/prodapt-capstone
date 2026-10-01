import { useEffect, useMemo, useRef } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, WarningCircle } from "@phosphor-icons/react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { Clause } from "@/lib/api/types";
import { MarkedText } from "@/components/HighlightMark";
import { ErrorNotice, Skeleton } from "@/components/Feedback";
import { formatDate } from "@/lib/format";
import { VersionDiff } from "./VersionDiff";

const kindLabel: Record<Clause["kind"], string | null> = {
  definition: "Definition",
  exception: "Exception",
  requirement: null,
  general: null,
};

/* One clause as it appears in the source viewer: big number in the margin, exact text. */
export function ClauseBody({
  clause: c,
  quote,
  play = true,
  headingLevel: H = "h2",
}: {
  clause: Clause;
  quote?: string | null;
  play?: boolean;
  headingLevel?: "h2" | "h3" | "p";
}) {
  return (
    <>
      <span className="tnum font-display text-4xl font-bold leading-none sm:text-5xl">
        {c.section_path[c.section_path.length - 1]}
      </span>
      <div>
        <H className="mt-2 text-lg font-semibold sm:mt-0">
          {c.heading}
          {kindLabel[c.kind] && <span className="ml-2 text-sm font-medium text-ink-2">{kindLabel[c.kind]}</span>}
        </H>
        <p className="mt-2 max-w-[68ch] text-[1.125rem] leading-[1.7]">
          <MarkedText text={c.text} quote={quote} play={play} delay={0.35} />
        </p>
        <p className="tnum mt-2 text-sm text-ink-2">
          {api.mode === "http" ? (
            <a
              href={`/api/v1/policy-versions/${encodeURIComponent(c.policy_version_id)}/source?page=${c.page_index + 1}`}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-4"
              aria-label={`Open original PDF page ${c.page_index + 1} for clause ${c.section_path.join(" / ")} (new tab)`}
            >
              Page {c.page_index + 1} · Original PDF
            </a>
          ) : `Page ${c.page_index + 1}`}
        </p>
      </div>
    </>
  );
}

export function PolicyDetail() {
  const { policyId = "", versionId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const linked = params.get("clause");
  const quote = params.get("q");
  const compareId = params.get("compare");
  const compare = useQuery({
    queryKey: ["policy-version", compareId],
    queryFn: () => api.getPolicyVersion(compareId!),
    enabled: Boolean(compareId),
    staleTime: Infinity,
  });
  const version = useQuery({ queryKey: ["policy-version", versionId], queryFn: () => api.getPolicyVersion(versionId), staleTime: Infinity });
  const list = useQuery({ queryKey: ["policies"], queryFn: () => api.listPolicies() });
  const policy = list.data?.find((p) => p.id === policyId);
  const clauseRefs = useRef(new Map<string, HTMLElement>());

  const sections = useMemo(() => {
    const out: { top: string; clauses: Clause[] }[] = [];
    for (const c of version.data?.clauses ?? []) {
      const top = c.section_path[0];
      const last = out[out.length - 1];
      if (last?.top === top) last.clauses.push(c);
      else out.push({ top, clauses: [c] });
    }
    return out;
  }, [version.data]);

  useEffect(() => {
    if (!linked || !version.data) return;
    const el = clauseRefs.current.get(linked);
    if (el) {
      el.scrollIntoView({ block: "center" });
      el.focus({ preventScroll: true });
    }
  }, [linked, version.data]);

  if (version.isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 md:px-8">
        <ErrorNotice title="This policy version could not be loaded" body="It may have been removed or you may not have access." onRetry={() => version.refetch()} />
      </div>
    );
  }

  const v = version.data;
  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-12">
      <Link to="/app/policies" className="inline-flex items-center gap-1.5 font-semibold underline decoration-1 underline-offset-4">
        <ArrowLeft size={16} aria-hidden /> Policies
      </Link>

      {!v ? (
        <div className="mt-8 space-y-4" aria-busy>
          <Skeleton className="h-14 w-2/3" />
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="mt-10 h-64" />
        </div>
      ) : (
        <>
          <h1 className="mt-6 max-w-[22ch] font-display text-[clamp(2.25rem,4.4vw,4rem)] font-bold leading-[1.02]">
            {v.policy_title}
          </h1>
          {params.get("published") && <p role="status" className="mt-4 border-2 border-met p-4">Published. New assessments can use this version from its effective date; earlier assessments keep their saved snapshot.</p>}
          {v.status === "draft" && api.mode === "http" && <div className="mt-5 font-semibold"><Link className="underline underline-offset-4" to={`/app/policies/manage/${encodeURIComponent(v.id)}`}>Review and publish draft</Link></div>}

          <div className="mt-10 grid gap-x-14 gap-y-10 lg:grid-cols-[13rem_minmax(0,1fr)_18rem]">
            <nav aria-label="Sections" className="hidden lg:block">
              <ol className="sticky top-24 space-y-1 border-l-2 border-ink">
                {v.clauses.map((c) => (
                  <li key={c.id}>
                    <a
                      href={`#${c.id}`}
                      onClick={(e) => {
                        e.preventDefault();
                        const next = new URLSearchParams(params);
                        next.set("clause", c.id);
                        next.delete("q");
                        setParams(next, { replace: true });
                        const target = clauseRefs.current.get(c.id);
                        target?.scrollIntoView({ block: "start" });
                        target?.focus({ preventScroll: true });
                      }}
                      className={clsx(
                        "tnum -ml-[2px] block border-l-2 py-1 pl-4 text-sm",
                        c.id === linked ? "border-ink font-semibold" : "border-transparent text-ink-2 hover:text-ink",
                      )}
                    >
                      {c.section_path[c.section_path.length - 1]} {c.heading}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>

            <article aria-label={`${v.policy_title} ${v.label}`} className="min-w-0">
              {linked && !v.clauses.some((c) => c.id === linked) && (
                <p role="status" className="mb-8 border-2 border-ink p-4">
                  The linked clause is not present in this policy version. Check the version or choose a section below.
                </p>
              )}
              {compareId && (
                <section aria-labelledby="diff-h" className="mb-12">
                  <h2 id="diff-h" className="font-display text-3xl font-semibold">
                    What changed
                  </h2>
                  <div className="mt-4">
                    {compare.isError ? (
                      <ErrorNotice
                        title="The comparison version could not be loaded"
                        body="It may have been removed or you may not have access. The current policy is still available below."
                        onRetry={() => compare.refetch()}
                      />
                    ) : compare.data ? (
                      compare.data.effective_from < v.effective_from ? (
                        <VersionDiff from={compare.data} to={v} />
                      ) : (
                        <VersionDiff from={v} to={compare.data} />
                      )
                    ) : (
                      <Skeleton className="h-40" />
                    )}
                  </div>
                </section>
              )}
              {v.extraction_warnings.map((w) => (
                <p key={w} className="mb-8 flex gap-3 bg-sheet p-4 text-sm">
                  <WarningCircle size={20} className="shrink-0 text-unknown" aria-hidden />
                  <span>
                    <span className="font-semibold">Extraction warning. </span>
                    {w}
                  </span>
                </p>
              ))}
              {v.clauses.length === 0 && (
                <div className="border-t-2 border-ink py-10">
                  <p className="font-display text-3xl font-bold">No clause text yet.</p>
                  <p className="mt-3 max-w-[56ch] text-ink-2">
                    This policy is listed in the demo corpus, but its clauses have not been authored or indexed. Paul.ez
                    will not cite it until they are.
                  </p>
                </div>
              )}
              {sections.map((s) => (
                <section key={s.top} className="border-t-2 border-ink pt-2">
                  {s.clauses.map((c) => {
                    const isLinked = c.id === linked;
                    const exact = isLinked && quote && c.text.includes(quote) ? quote : null;
                    return (
                      <div
                        key={c.id}
                        id={c.id}
                        ref={(el) => {
                          if (el) clauseRefs.current.set(c.id, el);
                        }}
                        tabIndex={-1}
                        className={clsx(
                          "grid scroll-mt-28 gap-x-6 py-7 outline-none sm:grid-cols-[5.5rem_minmax(0,1fr)]",
                          isLinked && !exact && "bg-[color-mix(in_oklab,var(--mark)_24%,transparent)] px-4",
                        )}
                      >
                        <ClauseBody clause={c} quote={exact} />
                      </div>
                    );
                  })}
                </section>
              ))}
            </article>

            <aside aria-label="Version details" className="lg:sticky lg:top-24 lg:self-start">
              {api.mode === "http" && (
                <a
                  href={`/api/v1/policy-versions/${encodeURIComponent(v.id)}/source`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mb-6 flex min-h-11 items-center justify-center border-2 border-ink px-3 font-semibold underline underline-offset-4"
                >
                  Open original PDF (new tab)
                </a>
              )}
              <div className="space-y-2">
                <label htmlFor="version" className="font-semibold">
                  Version
                </label>
                <select
                  id="version"
                  value={v.id}
                  onChange={(e) => navigate(`/app/policies/${policyId}/versions/${e.target.value}`)}
                  className="block h-12 w-full border-2 border-ink bg-sheet px-3"
                >
                  {(policy?.versions ?? [v]).map((x) => (
                    <option key={x.id} value={x.id} disabled={x.status === "draft" && x.index_status !== "ready"}>
                      {x.label}, from {formatDate(x.effective_from)}
                      {x.status === "draft" ? " (draft)" : ""}
                    </option>
                  ))}
                </select>
              </div>
              <dl className="mt-6 divide-y divide-rule border-y-2 border-ink text-sm">
                {[
                  ["Effective", `${formatDate(v.effective_from)}${v.effective_to ? ` to ${formatDate(v.effective_to)}` : " onwards"}`],
                  ["Status", v.status === "published" ? "Published" : v.status === "draft" ? "Draft" : "Superseded"],
                  ["Owner", policy?.owner ?? ""],
                  ["Category", policy?.category ?? ""],
                  ["Pages", String(v.pages)],
                  ["Clauses indexed", String(v.clauses.length)],
                ].map(([k, val]) => (
                  <div key={k} className="flex justify-between gap-4 py-2.5">
                    <dt className="text-ink-2">{k}</dt>
                    <dd className="tnum text-right font-semibold">{val}</dd>
                  </div>
                ))}
              </dl>
              {(policy?.versions ?? []).filter((x) => x.id !== v.id && x.status === "published").map((x) => (
                <Link
                  key={x.id}
                  to={compareId === x.id ? `/app/policies/${policyId}/versions/${v.id}` : `/app/policies/${policyId}/versions/${v.id}?compare=${x.id}`}
                  className="mt-4 flex h-11 items-center justify-center border-2 border-ink font-semibold hover:bg-ink hover:text-paper"
                >
                  {compareId === x.id ? "Hide comparison" : `Compare with ${x.label}`}
                </Link>
              ))}
              <p className="mt-4 text-sm text-ink-2">
                Fictional demo policy. Assessments pin the version that was in force on their as-of date.
              </p>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}
