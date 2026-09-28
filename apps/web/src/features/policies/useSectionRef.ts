import { useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Clause } from "@/lib/api/types";

/* "§4.2 v1" for a clause or citation, with version labels from the policy list. */
export function useSectionRef() {
  const policies = useQuery({ queryKey: ["policies"], queryFn: () => api.listPolicies(), staleTime: 5 * 60_000 });
  const labels = useMemo(
    () => new Map(policies.data?.flatMap((p) => p.versions.map((v) => [v.id, v.label] as const)) ?? []),
    [policies.data],
  );
  return useCallback(
    (c: Pick<Clause, "section_path" | "policy_version_id">) =>
      `§${c.section_path[c.section_path.length - 1]} ${labels.get(c.policy_version_id) ?? ""}`.trim(),
    [labels],
  );
}
