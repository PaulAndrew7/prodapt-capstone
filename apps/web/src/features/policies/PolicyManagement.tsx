import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Clause, ClauseReview, DraftReview, DraftReviewInput, RelationReview, UploadPolicyInput } from "@/lib/api/types";
import { Button, ButtonLink } from "@/components/Button";
import { ErrorNotice, Skeleton } from "@/components/Feedback";
import { todayIso } from "@/lib/format";

export const policyInput = "mt-1 block min-h-11 w-full border-2 border-ink bg-sheet px-3 py-2";
const errorText = (error: unknown) => error instanceof Error ? error.message : "Please try again.";

function Intro({ title }: { title: string }) {
  return <><Link to="/app/policies" className="font-semibold underline underline-offset-4">← Policies</Link>
    <h1 className="mt-5 font-display text-4xl font-bold md:text-5xl">{title}</h1></>;
}

export function PolicyManagement() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const policies = useQuery({ queryKey: ["policies"], queryFn: () => api.listPolicies() });
  const [policyId, setPolicyId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState({ title: "", category: "", business_area: "", owner: "", label: "v1", effective_from: todayIso(), effective_to: "" });
  const upload = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Choose a digital PDF.");
      const input: UploadPolicyInput = { label: metadata.label.trim(), effective_from: metadata.effective_from, effective_to: metadata.effective_to || null,
        ...(policyId ? { policy_id: policyId } : { title: metadata.title, category: metadata.category, business_area: metadata.business_area, owner: metadata.owner }) };
      return api.uploadPolicy(file, input);
    },
    onSuccess: (review) => {
      qc.setQueryData(["draft-review", review.version.id], review);
      void qc.invalidateQueries({ queryKey: ["policies"] });
      navigate(`/app/policies/manage/${review.version.id}`);
    },
  });
  const drafts = (policies.data ?? []).flatMap((p) => p.versions.filter((v) => v.status === "draft").map((v) => ({ ...v, title: p.title })));
  return <div className="mx-auto max-w-5xl px-4 py-10 md:px-8">
    <Intro title="Manage policies" />
    <p className="mt-4 max-w-[68ch] text-lg text-ink-2">Upload a new policy or replace a document with a new version. Review the exact extracted clauses before publishing. Existing assessments retain their original sources.</p>
    {api.mode === "fixture" ? <p className="mt-8 border-2 border-ink p-5">Policy management requires the live API. Fixture mode cannot upload or publish documents.</p> : <>
      <form className="mt-8 space-y-6 border-2 border-ink bg-sheet p-5 md:p-8" onSubmit={(event) => { event.preventDefault(); upload.mutate(); }}>
        <h2 className="font-display text-2xl font-semibold">Upload a digital PDF</h2>
        <label className="block font-semibold">Policy
          <select className={policyInput} value={policyId} onChange={(event) => {
            const id = event.target.value;
            setPolicyId(id);
            const p = policies.data?.find((item) => item.id === id);
            setMetadata((m) => ({ ...m, label: p ? `v${p.versions.length + 1}` : "v1" }));
          }}><option value="">Create a new policy</option>{policies.data?.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}</select>
        </label>
        {!policyId && <div className="grid gap-5 sm:grid-cols-2">{(["title", "category", "business_area", "owner"] as const).map((key) => <label key={key} className="font-semibold">{({ title: "Policy title", category: "Category", business_area: "Business area", owner: "Policy owner" })[key]}
          <input className={policyInput} required maxLength={200} value={metadata[key]} onChange={(event) => setMetadata((m) => ({ ...m, [key]: event.target.value }))} /></label>)}</div>}
        <div className="grid gap-5 sm:grid-cols-3">
          <label className="font-semibold">Version label<input className={policyInput} required maxLength={32} pattern="[A-Za-z0-9][A-Za-z0-9 ._-]{0,31}" value={metadata.label} onChange={(e) => setMetadata((m) => ({ ...m, label: e.target.value }))} /></label>
          <label className="font-semibold">Effective from<input type="date" className={policyInput} required value={metadata.effective_from} onChange={(e) => setMetadata((m) => ({ ...m, effective_from: e.target.value }))} /></label>
          <label className="font-semibold">Effective until (optional)<input type="date" className={policyInput} min={metadata.effective_from} value={metadata.effective_to} onChange={(e) => setMetadata((m) => ({ ...m, effective_to: e.target.value }))} /></label>
        </div>
        <label className="block font-semibold">Policy PDF<input className={`${policyInput} text-sm`} type="file" accept="application/pdf,.pdf" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
        <p className="text-sm text-ink-2">Digital PDFs with a text layer. Scans, encrypted files and malformed documents need correction before indexing. Uploading creates an unpublished draft.</p>
        {upload.isError && <p role="alert" className="text-violated">{errorText(upload.error)}</p>}
        <Button type="submit" variant="mark" loading={upload.isPending} disabled={!file || policies.isPending}>Upload and preview</Button>
        {upload.isPending && <p role="status">Extracting clauses and building the search index… Keep this page open.</p>}
      </form>
      <section className="mt-10">
        <h2 className="font-display text-2xl font-semibold">Drafts awaiting review</h2>
        {policies.isError ? <ErrorNotice title="Drafts could not be loaded" body={errorText(policies.error)} onRetry={() => policies.refetch()} /> : policies.isPending ? <Skeleton className="mt-4 h-12" /> : drafts.length ? <ul className="mt-4 divide-y divide-rule border-y-2 border-ink">{drafts.map((draft) => <li key={draft.id} className="flex flex-wrap items-center justify-between gap-3 py-4"><span>{draft.title} · {draft.label}</span><ButtonLink to={`/app/policies/manage/${draft.id}`} variant="outline" size="sm">Review draft</ButtonLink></li>)}</ul> : <p className="mt-4 text-ink-2">No drafts are waiting for review.</p>}
      </section>
    </>}
  </div>;
}

export function DraftPolicyReview() {
  const { versionId = "" } = useParams();
  const q = useQuery({ queryKey: ["draft-review", versionId], queryFn: () => api.getDraftReview(versionId), enabled: api.mode === "http" });
  return <div className="mx-auto max-w-6xl px-4 py-10 md:px-8"><Intro title="Review policy draft" />
    {api.mode !== "http" ? <p className="mt-8">Draft review requires the live API.</p> : q.isPending ? <Skeleton className="mt-8 h-32" /> : q.isError ? <ErrorNotice title="Draft could not be loaded" body={errorText(q.error)} onRetry={() => q.refetch()} /> : <DraftReviewEditor key={`${q.data.version.id}:${q.data.revision}`} review={q.data} />}
  </div>;
}

export function DraftReviewEditor({ review }: { review: DraftReview }) {
  const v = review.version;
  const qc = useQueryClient();
  const navigate = useNavigate();
  const policies = useQuery({ queryKey: ["policies"], queryFn: () => api.listPolicies() });
  const [label, setLabel] = useState(v.label);
  const [from, setFrom] = useState(v.effective_from);
  const [until, setUntil] = useState(v.effective_to ?? "");
  const [clauses, setClauses] = useState<Record<string, ClauseReview>>(() => Object.fromEntries(v.clauses.map((c) => [c.id, { kind: c.kind, candidate: review.candidate_clause_ids.includes(c.id) }])));
  const [relations, setRelations] = useState<RelationReview[]>(() => review.relations.map(({ source_clause_id, target_clause_id, relation, approved, rationale }) => ({ source_clause_id, target_clause_id, relation, approved, rationale })));
  const [confirmed, setConfirmed] = useState(review.review_complete);
  const [warnings, setWarnings] = useState(review.warnings_acknowledged);
  const [dirty, setDirty] = useState(false);
  const [targetVersion, setTargetVersion] = useState(v.id);
  const [newRelation, setNewRelation] = useState<RelationReview>({ source_clause_id: v.clauses[0]?.id ?? "", target_clause_id: "", relation: "references", approved: false, rationale: "" });
  const target = useQuery({ queryKey: ["policy-version", targetVersion], queryFn: () => api.getPolicyVersion(targetVersion), enabled: targetVersion !== v.id });
  const targetClauses = targetVersion === v.id ? v.clauses : target.data?.clauses ?? [];
  const changed = () => { setDirty(true); setConfirmed(false); };
  const save = useMutation({ mutationFn: () => {
    const input: DraftReviewInput = { label: label.trim(), effective_from: from, effective_to: until || null, expected_revision: review.revision, clauses, relations, review_confirmed: confirmed, acknowledge_warnings: warnings };
    return api.saveDraftReview(v.id, input);
  }, onSuccess: (data) => {
    qc.setQueryData(["draft-review", v.id], data);
    void qc.invalidateQueries({ queryKey: ["policy-version", v.id] });
    void qc.invalidateQueries({ queryKey: ["policies"] });
  } });
  const publish = useMutation({ mutationFn: () => api.publishPolicy(v.id, review.revision), onSuccess: (result) => {
    void qc.invalidateQueries({ queryKey: ["policies"] });
    void qc.invalidateQueries({ queryKey: ["policy-version", v.id] });
    void qc.invalidateQueries({ queryKey: ["policy-graph"] });
    void qc.invalidateQueries({ queryKey: ["draft-review", v.id] });
    navigate(`/app/policies/${v.policy_id}/versions/${v.id}?published=${result.snapshot_id}`);
  } });
  const locked = v.status !== "draft";
  if (locked) return <div className="mt-8 space-y-5"><p>This version is published and its source is immutable. Upload a replacement PDF as a new version to change its content.</p><ButtonLink to={`/app/policies/${v.policy_id}/versions/${v.id}`}>Open published version</ButtonLink></div>;
  return <form className="mt-8 space-y-8" onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
    <div className="border-2 border-ink bg-sheet p-5">
      <h2 className="font-display text-2xl font-semibold">{v.policy_title}</h2>
      <p className="mt-2 text-ink-2">Unpublished · {v.clauses.length} extracted clauses · {v.pages} pages. Classifications and approved links guide retrieval and local review; they do not establish applicability.</p>
      <a className="mt-3 inline-block font-semibold underline underline-offset-4" href={`/api/v1/policy-versions/${v.id}/source`} target="_blank" rel="noopener noreferrer">Open original PDF (new tab)</a>
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <label className="font-semibold">Version label<input className={policyInput} required pattern="[A-Za-z0-9][A-Za-z0-9 ._-]{0,31}" maxLength={32} value={label} onChange={(e) => { setLabel(e.target.value); changed(); }} /></label>
        <label className="font-semibold">Effective from<input type="date" className={policyInput} required value={from} onChange={(e) => { setFrom(e.target.value); changed(); }} /></label>
        <label className="font-semibold">Effective until (optional)<input type="date" className={policyInput} min={from} value={until} onChange={(e) => { setUntil(e.target.value); changed(); }} /></label>
      </div>
    </div>
    {v.extraction_warnings.length > 0 && <section className="border-2 border-unknown p-5"><h2 className="font-semibold">Extraction warnings</h2><ul className="mt-3 list-inside list-disc">{v.extraction_warnings.map((text, i) => <li key={i}>{text}</li>)}</ul><label className="mt-4 flex items-start gap-3"><input type="checkbox" checked={warnings} onChange={(e) => { setWarnings(e.target.checked); setDirty(true); }} className="mt-1 size-5 shrink-0" />I checked these warnings against the original PDF.</label></section>}
    <section><h2 className="font-display text-2xl font-semibold">Extracted clauses</h2><p className="mt-2 text-ink-2">Review each source. General clauses can still impose obligations: mark those as candidates. Definitions remain context.</p>
      <div className="mt-4 divide-y divide-rule border-y-2 border-ink">{v.clauses.map((c, i) => <details key={c.id} open={i === 0 ? true : undefined} className="py-4">
        <summary className="cursor-pointer text-lg font-semibold">§{c.section_path.at(-1)} {c.heading}</summary>
        <p className="mt-4 whitespace-pre-wrap leading-relaxed">{c.text}</p>
        <a className="mt-2 inline-block text-sm underline underline-offset-4" href={`/api/v1/policy-versions/${v.id}/source?page=${c.page_index + 1}`} target="_blank" rel="noopener noreferrer">Original page {c.page_index + 1} (new tab)</a>
        <div className="mt-4 grid items-end gap-4 sm:grid-cols-2">
          <label className="font-semibold">Classification for §{c.section_path.at(-1)}<select className={policyInput} value={clauses[c.id].kind} onChange={(event) => {
            const kind = event.target.value as Clause["kind"];
            setClauses((old) => ({ ...old, [c.id]: { kind, candidate: kind === "definition" ? false : kind === "general" ? old[c.id].candidate : true } })); changed();
          }}>{(["requirement", "exception", "definition", "general"] as const).map((kind) => <option key={kind} value={kind}>{kind}</option>)}</select></label>
          <label className="flex items-center gap-3 py-3"><input type="checkbox" className="size-5 shrink-0" checked={clauses[c.id].candidate} disabled={clauses[c.id].kind !== "general"} onChange={(e) => { setClauses((old) => ({ ...old, [c.id]: { ...old[c.id], candidate: e.target.checked } })); changed(); }} />Include §{c.section_path.at(-1)} in requirement checks</label>
        </div>
      </details>)}</div>
    </section>
    <section><h2 className="font-display text-2xl font-semibold">Clause relationships</h2><p className="mt-2 text-ink-2">Extracted links are proposals. Approve a link only after checking its source. Exceptions and overrides need a rationale. Cross-version links appear only when both endpoints are in scope.</p>
      <div className="mt-4 space-y-4">{relations.map((r, i) => <div key={`${r.source_clause_id}:${r.target_clause_id}:${r.relation}`} className="border-2 border-rule p-4">
        <p className="break-words font-semibold">{v.clauses.find((c) => c.id === r.source_clause_id)?.heading ?? r.source_clause_id} → {r.relation} → {review.relations.find((row) => row.target_clause_id === r.target_clause_id)?.target_heading ?? targetClauses.find((c) => c.id === r.target_clause_id)?.heading ?? r.target_clause_id}</p>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3"><label className="flex items-center gap-3"><input type="checkbox" className="size-5" checked={r.approved} onChange={(e) => { setRelations((rows) => rows.map((row, n) => n === i ? { ...row, approved: e.target.checked } : row)); changed(); }} />Approve for retrieval</label><Button size="sm" type="button" variant="ghost" onClick={() => { setRelations((rows) => rows.filter((_, n) => n !== i)); changed(); }}>Remove link</Button></div>
        <label className="mt-3 block text-sm font-semibold">Relationship rationale<input className={policyInput} maxLength={1000} required={r.approved && r.relation !== "references"} value={r.rationale} onChange={(e) => { setRelations((rows) => rows.map((row, n) => n === i ? { ...row, rationale: e.target.value } : row)); changed(); }} /></label>
      </div>)}</div>
      <details className="mt-5 border-2 border-ink p-4"><summary className="cursor-pointer font-semibold">Add a relationship</summary>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="font-semibold">Source clause<select className={policyInput} value={newRelation.source_clause_id} onChange={(e) => setNewRelation((r) => ({ ...r, source_clause_id: e.target.value }))}>{v.clauses.map((c) => <option value={c.id} key={c.id}>§{c.section_path.at(-1)} {c.heading}</option>)}</select></label>
          <label className="font-semibold">Relationship type<select className={policyInput} value={newRelation.relation} onChange={(e) => setNewRelation((r) => ({ ...r, relation: e.target.value as RelationReview["relation"] }))}><option>references</option><option>excepts</option><option>overrides</option></select></label>
          <label className="font-semibold">Target version<select className={policyInput} value={targetVersion} onChange={(e) => { setTargetVersion(e.target.value); setNewRelation((r) => ({ ...r, target_clause_id: "" })); }}><option value={v.id}>This draft · {v.label}</option>{policies.data?.flatMap((p) => p.versions.filter((row) => row.status !== "draft").map((row) => <option key={row.id} value={row.id}>{p.title} · {row.label}</option>))}</select></label>
          <label className="font-semibold">Target clause<select className={policyInput} value={newRelation.target_clause_id} onChange={(e) => setNewRelation((r) => ({ ...r, target_clause_id: e.target.value }))}><option value="">Select a clause</option>{targetClauses.map((c) => <option key={c.id} value={c.id}>§{c.section_path.at(-1)} {c.heading}</option>)}</select></label>
        </div>
        {target.isError && <p role="alert" className="mt-3 text-violated">{errorText(target.error)}</p>}
        <Button className="mt-4" size="sm" type="button" variant="outline" disabled={!newRelation.target_clause_id || newRelation.source_clause_id === newRelation.target_clause_id || relations.some((r) => r.source_clause_id === newRelation.source_clause_id && r.target_clause_id === newRelation.target_clause_id && r.relation === newRelation.relation)} onClick={() => { setRelations((rows) => [...rows, { ...newRelation }]); changed(); }}>Add proposed link</Button>
      </details>
    </section>
    <div className="border-2 border-ink bg-sheet p-5">
      <label className="flex items-start gap-3 font-semibold"><input type="checkbox" className="mt-1 size-5 shrink-0" checked={confirmed} onChange={(e) => { setConfirmed(e.target.checked); setDirty(true); }} />I reviewed all extracted clauses, candidate classifications and relationship approvals against the source.</label>
      <p className="mt-3 text-sm text-ink-2">Save your review before publishing. Publication creates a new snapshot; it does not rewrite earlier assessments. Content changes require a replacement PDF.</p>
      {(save.isError || publish.isError) && <p role="alert" className="mt-4 text-violated">{errorText(save.error ?? publish.error)}</p>}
      <div className="mt-5 flex flex-wrap gap-4"><Button type="submit" variant="outline" loading={save.isPending} disabled={publish.isPending}>Save draft review</Button><Button type="button" variant="mark" loading={publish.isPending} disabled={dirty || !review.review_complete || (v.extraction_warnings.length > 0 && !review.warnings_acknowledged) || save.isPending} onClick={() => publish.mutate()}>Publish policy version</Button></div>
      {review.review_complete && !dirty && <p role="status" className="mt-3 text-met">Review saved. This version is ready to publish{v.extraction_warnings.length && !warnings ? " after acknowledging extraction warnings" : ""}.</p>}
    </div>
  </form>;
}
