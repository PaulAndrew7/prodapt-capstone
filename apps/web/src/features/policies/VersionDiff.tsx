import type { PolicyVersion } from "@/lib/api/types";
import { HighlightMark } from "@/components/HighlightMark";
import { formatDate } from "@/lib/format";

type Row =
  | { kind: "added"; number: string; heading: string; text: string }
  | { kind: "removed"; number: string; heading: string; text: string }
  | { kind: "changed"; number: string; heading: string; before: string; after: string };

const key = (path: string[]) => path.join(".");

/* Deterministic clause-level diff keyed by section path. No generated explanation. */
export function diffVersions(from: PolicyVersion, to: PolicyVersion): Row[] {
  const a = new Map(from.clauses.map((c) => [key(c.section_path), c]));
  const b = new Map(to.clauses.map((c) => [key(c.section_path), c]));
  const rows: Row[] = [];
  for (const [k, c] of b) {
    const old = a.get(k);
    const number = c.section_path[c.section_path.length - 1];
    if (!old) rows.push({ kind: "added", number, heading: c.heading, text: c.text });
    else if (old.text !== c.text) rows.push({ kind: "changed", number, heading: c.heading, before: old.text, after: c.text });
  }
  for (const [k, c] of a) {
    if (!b.has(k)) rows.push({ kind: "removed", number: c.section_path[c.section_path.length - 1], heading: c.heading, text: c.text });
  }
  return rows;
}

export function VersionDiff({ from, to, play = true }: { from: PolicyVersion; to: PolicyVersion; play?: boolean }) {
  const rows = diffVersions(from, to);
  const unchanged = to.clauses.length - rows.filter((r) => r.kind !== "removed").length;
  return (
    <div>
      <p className="tnum text-sm text-ink-2">
        {from.label} (from {formatDate(from.effective_from)}) compared with {to.label} (from {formatDate(to.effective_from)})
      </p>
      {rows.length === 0 ? (
        <p className="mt-4 font-semibold">No clause changed between these versions.</p>
      ) : (
        <ul className="mt-4 divide-y divide-rule border-y-2 border-ink">
          {rows.map((r) => (
            <li key={`${r.kind}-${r.number}`} className="grid gap-x-6 py-5 sm:grid-cols-[5rem_minmax(0,1fr)]">
              <span className="tnum font-display text-4xl font-bold leading-none">{r.number}</span>
              <div>
                <p className="font-semibold">
                  {r.heading}{" "}
                  <span className={r.kind === "removed" ? "text-violated" : "text-ink-2"}>
                    {r.kind === "added" ? "Added" : r.kind === "removed" ? "Removed" : "Wording changed"}
                  </span>
                </p>
                {r.kind === "added" && (
                  <p className="mt-2 max-w-[64ch] leading-relaxed">
                    <HighlightMark play={play} delay={0.3}>
                      {r.text}
                    </HighlightMark>
                  </p>
                )}
                {r.kind === "removed" && <s className="mt-2 block max-w-[64ch] text-ink-2 decoration-violated decoration-2">{r.text}</s>}
                {r.kind === "changed" && (
                  <>
                    <s className="mt-2 block max-w-[64ch] text-ink-2 decoration-violated decoration-2">{r.before}</s>
                    <p className="mt-2 max-w-[64ch]">
                      <HighlightMark play={play} delay={0.3}>
                        {r.after}
                      </HighlightMark>
                    </p>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-sm text-ink-2">{unchanged} clauses unchanged. Past assessments keep citing the version they used.</p>
    </div>
  );
}
