import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import type { GraphNode, PolicyGraph as Graph } from "@/lib/api/types";
import { api } from "@/lib/api";
import { ButtonLink } from "@/components/Button";
import { ErrorNotice, Skeleton } from "@/components/Feedback";
import { todayIso } from "@/lib/format";
import { policyInput } from "./PolicyManagement";

const columns: Record<GraphNode["kind"], number> = { policy: 0, case: 0, version: 1, clause: 2, finding: 3 };
const words = (value: string) => value.replaceAll("_", " ");
function nodeLines(label: string): string[] {
  const lines = [""];
  for (const word of label.split(/\s+/)) {
    const i = lines.length - 1;
    if ((lines[i] + " " + word).trim().length > 28 && lines[i]) lines.push(word);
    else lines[i] = (lines[i] + " " + word).trim();
  }
  return [lines[0]?.slice(0, 28) ?? "", (lines[1]?.slice(0, 25) ?? "") + (lines.length > 2 ? "…" : "")];
}

export function PolicyGraphView({ graph }: { graph: Graph }) {
  const [selectedId, setSelectedId] = useState<string | null>(graph.nodes.find((n) => n.kind === "clause")?.id ?? null);
  const selected = graph.nodes.find((n) => n.id === selectedId);
  const layout = useMemo(() => {
    const counts = [0, 0, 0, 0];
    const positions = new Map(graph.nodes.map((node) => {
      const column = columns[node.kind];
      return [node.id, { x: 24 + column * 265, y: 52 + counts[column]++ * 96 }];
    }));
    return { positions, height: Math.max(450, Math.max(...counts) * 96 + 80) };
  }, [graph]);
  const name = (id: string) => graph.nodes.find((n) => n.id === id)?.label ?? id;
  const links = graph.edges.filter((edge) => edge.kind !== "contains");
  if (!graph.nodes.length) return <p className="mt-8 border-2 border-ink p-6">No published clauses for this policy in the selected snapshot and date.</p>;
  return <>
    <div className="mt-6 grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <section className="min-w-0 border-2 border-ink bg-sheet" aria-label="Interactive graph">
        <p className="border-b border-rule px-4 py-3 text-sm text-ink-2">Select a node to inspect its source. Scroll the diagram, or use the relationship list below. Dashed links are unreviewed.</p>
        <div className="max-h-[650px] overflow-auto" tabIndex={0} aria-label="Scrollable policy graph">
          <svg viewBox={`0 0 1080 ${layout.height}`} style={{ height: layout.height }} className="w-full min-w-[900px]" role="group" aria-label="Policy relationship nodes">
            <title>Stored policy relationships</title>
            <defs><marker id="policy-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="context-stroke" /></marker></defs>
            {["Policies / cases", "Policy versions", "Source clauses", "Saved findings"].map((text, i) => <text key={text} x={24 + i * 265} y={28} className="fill-ink-2 text-[13px] font-semibold">{text}</text>)}
            {graph.edges.map((edge) => {
              const a = layout.positions.get(edge.source), b = layout.positions.get(edge.target);
              if (!a || !b) return null;
              const same = a.x === b.x;
              const fromX = same ? a.x + 230 : a.x + 225, toX = same ? b.x + 230 : b.x - 4;
              const bend = same ? a.x + 259 : (fromX + toX) / 2;
              const active = edge.source === selectedId || edge.target === selectedId;
              return <path key={edge.id} aria-hidden d={`M${fromX},${a.y + 35} C${bend},${a.y + 35} ${bend},${b.y + 35} ${toX},${b.y + 35}`} fill="none" className={edge.kind === "contains" ? "stroke-rule" : edge.kind === "excepts" || edge.kind === "overrides" ? "stroke-unknown" : "stroke-ink-2"} strokeWidth={active ? 3 : 1.5} strokeDasharray={edge.approved ? undefined : "5 4"} opacity={selectedId && !active ? 0.35 : 1} markerEnd="url(#policy-arrow)" />;
            })}
            {graph.nodes.map((node) => {
              const pos = layout.positions.get(node.id)!, lines = nodeLines(node.label);
              return <g key={node.id} transform={`translate(${pos.x},${pos.y})`} tabIndex={0} role="button" aria-label={`${node.kind}: ${node.label}`} aria-pressed={selectedId === node.id} className="group cursor-pointer outline-none" onClick={() => setSelectedId(node.id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedId(node.id); } }}>
                <rect width="225" height="72" className={`${selectedId === node.id ? "fill-mark" : "fill-sheet"} stroke-ink group-focus-visible:stroke-unknown`} strokeWidth="2" />
                <text x="10" y="16" className="fill-ink-2 text-[10px] font-semibold uppercase">{node.kind}{node.status ? ` · ${words(node.status)}` : ""}</text>
                <text x="10" y="36" className="fill-ink text-[13px] font-semibold"><tspan x="10">{lines[0]}</tspan><tspan x="10" dy="17">{lines[1]}</tspan></text>
              </g>;
            })}
          </svg>
        </div>
      </section>
      <aside className="min-w-0 border-2 border-ink p-5" aria-label="Selected graph node">
        {selected ? <><p className="text-sm font-semibold text-ink-2">{words(selected.kind)}{selected.status ? ` · ${words(selected.status)}` : ""}</p><h2 className="mt-3 break-words font-display text-2xl font-semibold">{selected.label}</h2>{selected.text && <p className="mt-4 whitespace-pre-wrap leading-relaxed">{selected.text}</p>}<Link className="mt-5 block font-semibold underline underline-offset-4" to={selected.href}>Open {selected.kind === "finding" ? "assessment" : selected.kind}</Link>{selected.source_url && <a className="mt-3 block font-semibold underline underline-offset-4" href={selected.source_url} target="_blank" rel="noopener noreferrer">Open original PDF (new tab)</a>}<p className="mt-5 text-sm text-ink-2">These links record source structure and review decisions. They do not independently prove applicability or a correct interpretation.</p></> : <p>Select a node to view its source.</p>}
      </aside>
    </div>
    <details className="mt-6 border-2 border-ink p-5" open><summary className="cursor-pointer font-semibold">Relationship list · {links.length} links</summary>
      {links.length ? <ul className="mt-4 divide-y divide-rule">{links.map((edge) => <li key={edge.id} className="py-4"><div className="flex flex-wrap items-center gap-2"><button className="text-left font-semibold underline underline-offset-4" onClick={() => setSelectedId(edge.source)}>{name(edge.source)}</button><span className="text-sm text-ink-2">→ {edge.kind} →</span><button className="text-left font-semibold underline underline-offset-4" onClick={() => setSelectedId(edge.target)}>{name(edge.target)}</button></div><p className="mt-1 text-sm text-ink-2">{edge.kind === "supports" ? "Recorded assessment link" : edge.approved ? "Reviewed relationship" : "Unreviewed relationship"} · {words(edge.provenance)}</p></li>)}</ul> : <p className="mt-4 text-ink-2">This policy has no stored cross-reference links in scope. Its containment structure is shown above.</p>}
    </details>
    {graph.truncated && <p role="status" className="mt-4 text-unknown">Showing 60 of {graph.total_clauses} clauses. Focus on another policy to explore additional sources.</p>}
  </>;
}

export function PolicyKnowledgeGraph() {
  const [params, setParams] = useSearchParams();
  const caseId = params.get("case_id") ?? undefined;
  const input = { policy_id: params.get("policy_id") ?? undefined, as_of: params.get("as_of") ?? todayIso(), snapshot_id: params.get("snapshot_id") ?? undefined, case_id: caseId };
  const policies = useQuery({ queryKey: ["policies"], queryFn: () => api.listPolicies() });
  const q = useQuery({ queryKey: ["policy-graph", input], queryFn: () => api.getPolicyGraph(input), enabled: api.mode === "http" });
  const change = (key: string, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next); };
  return <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8">
    <Link to="/app/policies" className="font-semibold underline underline-offset-4">← Policies</Link>
    <h1 className="mt-5 font-display text-4xl font-bold md:text-5xl">Policy knowledge graph</h1>
    <p className="mt-4 max-w-[70ch] text-lg text-ink-2">Explore the clauses, versions and stored relationships behind an assessment. Every source node opens its original policy evidence.</p>
    {api.mode !== "http" ? <p className="mt-8 border-2 border-ink p-5">The stored knowledge graph requires the live API. Fixture mode does not query real policy relationships.</p> : <>
      <div className="mt-7 grid items-end gap-4 sm:grid-cols-[minmax(0,1fr)_14rem_auto]">
        <label className="font-semibold">Focus policy<select className={policyInput} value={input.policy_id ?? q.data?.policy_id ?? ""} onChange={(e) => change("policy_id", e.target.value)}><option value="">Choose a policy</option>{policies.data?.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
        <label className="font-semibold">Assessment date<input type="date" className={policyInput} value={caseId ? q.data?.as_of ?? input.as_of : input.as_of} disabled={Boolean(caseId)} onChange={(e) => change("as_of", e.target.value)} /></label>
        <ButtonLink variant="outline" to="/app/policies/manage">Manage policies</ButtonLink>
      </div>
      {q.isPending ? <Skeleton className="mt-8 h-96" /> : q.isError ? <ErrorNotice title="Graph could not be loaded" body={q.error instanceof Error ? q.error.message : "Try again."} onRetry={() => q.refetch()} /> : <><p className="mt-5 break-all text-sm text-ink-2">{caseId ? "Saved assessment snapshot" : "Policy snapshot"}: {q.data.snapshot_id} · {q.data.as_of} · {q.data.nodes.length} nodes · {q.data.edges.length} edges</p>{caseId && <Link className="mt-2 inline-block font-semibold underline" to={`/app/cases/${caseId}`}>Back to assessment</Link>}<PolicyGraphView key={`${q.data.snapshot_id}:${q.data.policy_id}:${q.data.as_of}`} graph={q.data} /></>}
    </>}
  </div>;
}
