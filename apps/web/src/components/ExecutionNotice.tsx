import type { ExecutionInfo } from "@/lib/api/types";

export function ExecutionNotice({ execution, lookup = false }: { execution?: ExecutionInfo | null; lookup?: boolean }) {
  if (execution?.mode !== "local_review") return null;
  const reason = execution.reason === "model_failure"
    ? `The model request failed${execution.failed_stage ? ` during ${execution.failed_stage}` : ""}; the app continued locally.`
    : execution.reason === "forced_offline"
      ? "Offline mode is selected. No language model is used."
      : "No language model is configured. The app is working locally.";
  return (
    <aside aria-label={lookup ? "Local source mode" : "Local review mode"} className="my-4 border-2 border-ink bg-sheet p-4 text-sm">
      <p className="font-semibold">{lookup ? "Local source excerpts" : "Local evidence review"}</p>
      <p className="mt-1">{reason}</p>
      <p className="mt-2 text-ink-2">
        {lookup
          ? "These are exact retrieved excerpts. Read the sources to interpret how they answer your question."
          : "Source checks and your explicit confirmations decide this result. The local engine does not interpret the scenario; unconfirmed checks stay unknown."}
      </p>
    </aside>
  );
}
