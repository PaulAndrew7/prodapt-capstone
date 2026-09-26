import type { Citation } from "@/lib/api/types";
import { clauseById } from "./policies";

/* Builds a citation from a stored clause and checks the quote is an exact span of it. */
export function cite(id: string, clauseId: string, quote: string): Citation {
  const c = clauseById(clauseId);
  if (!c) throw new Error(`Unknown clause ${clauseId}`);
  if (!c.text.includes(quote)) throw new Error(`Quote not in clause ${clauseId}`);
  return {
    id,
    policy_version_id: c.policy_version_id,
    clause_id: c.id,
    page_index: c.page_index,
    section_path: c.section_path,
    quote,
    source_url: `/api/v1/policy-versions/${c.policy_version_id}/source?page=${c.page_index + 1}`,
  };
}
