import { PolicyAsk } from "./PolicyAsk";

export function AskPage() {
  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-14">
      <h1 className="font-display text-[clamp(2.75rem,5vw,4.5rem)] font-bold leading-none">Ask a question</h1>
      <p className="mt-4 max-w-[60ch] text-lg text-ink-2">
        A short answer from the fictional Kestrel Mutual policies, with the clauses behind it. To check a plan
        against the policies, start a case instead.
      </p>
      <div className="mt-10">
        <PolicyAsk />
      </div>
    </div>
  );
}
