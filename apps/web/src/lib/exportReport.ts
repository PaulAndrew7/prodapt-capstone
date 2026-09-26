import type { CaseDetail } from "@/lib/api/types";

/* JSON export of an immutable assessment with the facts and snapshot it used. */
export function exportReport(detail: CaseDetail) {
  if (!detail.assessment) return;
  const payload = {
    generated_at: new Date().toISOString(),
    note: "Demo export. Policies are fictional. Review state is shown as recorded; nothing here certifies compliance.",
    case: { id: detail.id, title: detail.title, as_of: detail.as_of, scope: detail.scope },
    facts: detail.facts,
    assessment: detail.assessment,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `clause-assessment-${detail.assessment.run_id}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
