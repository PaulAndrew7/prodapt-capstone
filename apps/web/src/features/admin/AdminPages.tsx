import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { DownloadSimple } from "@phosphor-icons/react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { CaseDetail } from "@/lib/api/types";
import { AssessmentStatusWord } from "@/components/Status";
import { Button } from "@/components/Button";
import { EmptyState, Skeleton } from "@/components/Feedback";
import { formatDate } from "@/lib/format";
import { exportReport } from "@/lib/exportReport";
import { useThemePref, type ThemePref } from "@/app/providers";
import { useAvatarPref } from "@/features/avatar/avatarPref";

function PageTitle({ children, lead }: { children: React.ReactNode; lead: string }) {
  return (
    <>
      <h1 className="font-display text-[clamp(2.75rem,5vw,4.5rem)] font-bold leading-none">{children}</h1>
      <p className="mt-4 max-w-[62ch] text-lg text-ink-2">{lead}</p>
    </>
  );
}

export function Reports() {
  const list = useQuery({ queryKey: ["cases"], queryFn: () => api.listCases() });
  const done = (list.data ?? []).filter((c) => c.run_state === "completed");
  const details = useQueries({ queries: done.map((c) => ({ queryKey: ["case", c.id], queryFn: () => api.getCase(c.id) })) });
  const rows = details.map((d) => d.data).filter((d): d is CaseDetail => Boolean(d?.assessment));
  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-14">
      <PageTitle lead="Machine-readable exports of completed assessments, with the facts, citations, policy snapshot and review state they were based on.">
        Reports
      </PageTitle>
      <div className="mt-10">
        {list.isPending || details.some((d) => d.isPending) ? (
          <Skeleton className="h-48" />
        ) : rows.length === 0 ? (
          <EmptyState title="No reports yet." body="Finish an assessment to export it." />
        ) : (
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Exportable assessments</caption>
            <thead className="hidden md:table-header-group">
              <tr className="border-b-2 border-ink text-sm">
                <th scope="col" className="py-3 pr-6 font-semibold">Case</th>
                <th scope="col" className="py-3 pr-6 font-semibold">Result</th>
                <th scope="col" className="py-3 pr-6 font-semibold">As of</th>
                <th scope="col" className="py-3 pr-6 font-semibold">Snapshot</th>
                <th scope="col" className="py-3 font-semibold"><span className="sr-only">Export</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule border-t-2 border-ink md:border-t-0">
              {rows.map((d) => (
                <tr key={d.id} className="grid gap-1 py-4 md:table-row md:py-0">
                  <td className="md:py-4 md:pr-6">
                    <Link to={`/app/cases/${d.id}`} className="font-semibold underline-offset-4 hover:underline">
                      {d.title}
                    </Link>
                  </td>
                  <td className="md:py-4 md:pr-6"><AssessmentStatusWord status={d.assessment!.status} /></td>
                  <td className="tnum md:py-4 md:pr-6">{formatDate(d.as_of)}</td>
                  <td className="tnum text-sm text-ink-2 md:py-4 md:pr-6">{d.policy_snapshot_id}</td>
                  <td className="md:py-4 md:text-right">
                    <Button variant="outline" size="sm" onClick={() => exportReport(d)} icon={<DownloadSimple size={16} aria-hidden />}>
                      Export report
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const METRICS: [string, string][] = [
  ["Clause recall at 10", "Share of the gold clauses retrieved in the top ten results, over answerable cases."],
  ["Citation reference validity", "Citations that resolve to the correct authorized version and span."],
  ["Citation support precision", "Cited claims that the cited text actually supports, checked by a person."],
  ["Requirement macro-F1", "Agreement with gold labels across met, violated, unknown, not applicable and conflict."],
  ["False-compliant rate", "Non-compliant gold cases the system called compliant within scope."],
  ["Abstention precision and recall", "Whether evidence-poor cases are recognized without refusing answerable ones."],
  ["Latency and cost per run", "Wall-clock time by stage and total, and model usage per completed run."],
];

export function Evaluation() {
  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-14">
      <PageTitle lead="Measured quality on held-out scenarios. Only results from a real evaluation run appear on this page.">
        Evaluation
      </PageTitle>
      <div className="mt-12 grid gap-x-16 gap-y-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <section aria-labelledby="eval-empty">
          <h2 id="eval-empty" className="font-display text-3xl font-bold leading-tight">
            No measured results yet.
          </h2>
          <p className="mt-3 max-w-[52ch] text-ink-2">
            Results appear after the evaluation harness runs against the frozen scenario set. Until then nothing is
            estimated or filled in.
          </p>
          <p className="mt-6 text-sm font-semibold">Run it from the repository root</p>
          <pre tabIndex={0} aria-label="Evaluation command" className="mt-2 overflow-x-auto bg-ink p-4 text-sm text-paper">
            <code>docker compose run --rm api python -m app.cli evaluate --config evals/configs/baseline.yaml</code>
          </pre>
        </section>
        <section aria-labelledby="metrics-h">
          <h2 id="metrics-h" className="font-display text-2xl font-semibold">
            What will be measured
          </h2>
          <dl className="mt-4 divide-y divide-rule border-y-2 border-ink">
            {METRICS.map(([k, v]) => (
              <div key={k} className="grid gap-1 py-3 sm:grid-cols-[14rem_minmax(0,1fr)] sm:gap-6">
                <dt className="font-semibold">{k}</dt>
                <dd className="text-ink-2">{v}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  );
}

function Choice<T extends string>({
  name,
  value,
  options,
  onChange,
}: {
  name: string;
  value: T;
  options: { id: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => (
        <label
          key={o.id}
          className={clsx(
            "flex h-11 cursor-pointer items-center border-2 px-4 font-semibold transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-ink",
            value === o.id ? "border-ink bg-ink text-paper" : "border-ink/60 hover:border-ink",
          )}
        >
          <input type="radio" name={name} value={o.id} checked={value === o.id} onChange={() => onChange(o.id)} className="sr-only" />
          {o.label}
        </label>
      ))}
    </div>
  );
}

export function Settings() {
  const { pref, setPref } = useThemePref();
  const avatar = useAvatarPref();
  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-14">
      <PageTitle lead="Preferences are stored in this browser only.">Settings</PageTitle>
      <div className="mt-12 max-w-3xl divide-y divide-rule border-y-2 border-ink">
        <fieldset className="grid gap-4 py-6 md:grid-cols-[14rem_minmax(0,1fr)]">
          <legend className="sr-only">Theme</legend>
          <p className="font-semibold" aria-hidden>Theme</p>
          <div>
            <Choice<ThemePref>
              name="theme"
              value={pref}
              onChange={setPref}
              options={[
                { id: "system", label: "System" },
                { id: "light", label: "Light" },
                { id: "dark", label: "Dark" },
              ]}
            />
            <p className="mt-2 text-sm text-ink-2">System follows your device setting.</p>
          </div>
        </fieldset>
        <fieldset className="grid gap-4 py-6 md:grid-cols-[14rem_minmax(0,1fr)]">
          <legend className="sr-only">Assistant figure</legend>
          <p className="font-semibold" aria-hidden>Assistant figure</p>
          <div>
            <Choice<"on" | "off">
              name="avatar"
              value={avatar.enabled ? "on" : "off"}
              onChange={(v) => avatar.setEnabled(v === "on")}
              options={[
                { id: "on", label: "Show" },
                { id: "off", label: "Hide" },
              ]}
            />
            <p className="mt-2 text-sm text-ink-2">Everything works without it. It reacts only to your actions and real run progress.</p>
          </div>
        </fieldset>
        <div className="grid gap-4 py-6 md:grid-cols-[14rem_minmax(0,1fr)]">
          <p className="font-semibold">Motion</p>
          <p className="text-ink-2">Clause follows your system&rsquo;s reduced motion setting. With it on, highlights and verdicts appear without animation.</p>
        </div>
        <div className="grid gap-4 py-6 md:grid-cols-[14rem_minmax(0,1fr)]">
          <p className="font-semibold">Data source</p>
          <p className="text-ink-2">
            {api.mode === "fixture"
              ? "Fixture data. Runs replay authored scenarios; no model provider is called."
              : "Live compliance service."}
          </p>
        </div>
      </div>
    </div>
  );
}
