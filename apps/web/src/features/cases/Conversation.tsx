import { useEffect, useRef, useState } from "react";
import { ArrowUp, Question } from "@phosphor-icons/react";
import clsx from "clsx";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ClarificationQuestion, Clause, Fact, Message } from "@/lib/api/types";
import { Button } from "@/components/Button";
import { factOriginLabel } from "@/lib/status";
import { useSectionRef } from "@/features/policies/useSectionRef";

export function Transcript({ messages, autoScroll = true }: { messages: Message[]; autoScroll?: boolean }) {
  const end = useRef<HTMLDivElement>(null);
  const seen = useRef(messages.length);
  // Follow new messages only; never move the page on first load.
  useEffect(() => {
    if (autoScroll && messages.length > seen.current) end.current?.scrollIntoView({ block: "nearest" });
    seen.current = messages.length;
  }, [messages.length, autoScroll]);
  return (
    <div>
    <ol className="space-y-6" aria-label="Conversation">
      {messages.map((m) => (
        <li key={m.id}>
          <p className={clsx("text-sm font-semibold", m.role === "user" ? "text-ink" : "text-ink-2")}>
            {m.role === "user" ? "You" : "Clause"}
          </p>
          <p className={clsx("mt-1 max-w-[62ch]", m.role === "user" ? "text-[1.0625rem] leading-relaxed" : "text-ink-2")}>
            {m.text}
          </p>
        </li>
      ))}
    </ol>
      <div ref={end} />
    </div>
  );
}

function OriginTag({ fact }: { fact: Fact }) {
  const styles = {
    provided: "border-ink text-ink",
    inferred: "border-dashed border-ink text-ink",
    unknown: "border-unknown text-unknown",
  }[fact.origin];
  return (
    <span className={clsx("inline-flex h-6 items-center gap-1 border-[1.5px] px-1.5 text-xs font-semibold", styles)}>
      {fact.origin === "unknown" && <Question size={12} aria-hidden />}
      {factOriginLabel[fact.origin]}
      {fact.origin === "inferred" && !fact.confirmed && ", unconfirmed"}
    </span>
  );
}

export function FactList({ facts }: { facts: Fact[] }) {
  if (!facts.length) return null;
  return (
    <section aria-labelledby="facts-h">
      <h3 id="facts-h" className="font-display text-xl font-semibold">
        Facts
      </h3>
      <dl className="mt-3 divide-y divide-rule border-y-2 border-ink">
        {facts.map((f) => (
          <div key={f.id} className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)] gap-x-4 gap-y-1 py-3 sm:grid-cols-[minmax(0,9rem)_minmax(0,1fr)_auto]">
            <dt className="text-sm text-ink-2">{f.label}</dt>
            <dd className={clsx("font-medium", f.value === null && "text-ink-2")}>{f.value ?? "Not known yet"}</dd>
            <dd className="col-start-2 sm:col-start-3 sm:row-start-1">
              <OriginTag fact={f} />
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export const DONT_KNOW = "__dont_know__";

export function ClarificationBlock({
  questions,
  onSubmit,
  submitting,
  onOpenClause,
  initialAnswers = {},
  localReview = false,
  onFinishLocal,
}: {
  questions: ClarificationQuestion[];
  onSubmit: (answers: Record<string, string | null>) => void;
  submitting: boolean;
  onOpenClause: (clause: Clause) => void;
  initialAnswers?: Record<string, string>;
  localReview?: boolean;
  onFinishLocal?: () => void;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>(initialAnswers);
  const clauseRef = useSectionRef();
  // The clause that makes each question matter, so the requester can read it first.
  const refs = [...new Set(questions.map((q) => q.clause_ref).filter(Boolean))];
  const clauseQueries = useQueries({
    queries: refs.map((id) => ({ queryKey: ["clause", id], queryFn: () => api.getClause(id), staleTime: Infinity })),
  });
  const clauses = new Map(clauseQueries.filter((q) => q.data).map((q) => [q.data!.id, q.data!]));
  const complete = questions.every((q) => (answers[q.id] ?? "").trim().length > 0);

  return (
    <section aria-labelledby="clarify-h" className="bg-sheet p-5 outline-2 outline-ink md:p-6">
      <h3 id="clarify-h" className="font-display text-2xl font-semibold leading-tight">
        {localReview ? `${questions.length} local review checks` : `${questions.length === 1 ? "One question" : `${questions.length} questions`} before I finish`}
      </h3>
      <p className="mt-1 text-ink-2">{localReview ? "Confirm each clause after reading its source. More retrieved checks may follow. " : "Answer what you know. "}&ldquo;I don&rsquo;t know&rdquo; is a valid answer.</p>
      <form
        className="mt-5 space-y-7"
        onSubmit={(e) => {
          e.preventDefault();
          if (!complete) return;
          onSubmit(
            Object.fromEntries(questions.map((q) => [q.id, answers[q.id] === DONT_KNOW ? null : answers[q.id]])),
          );
        }}
      >
        {questions.map((q, i) => {
          const clause = clauses.get(q.clause_ref);
          const value = answers[q.id] ?? "";
          const set = (v: string) => setAnswers((a) => ({ ...a, [q.id]: v }));
          return (
            <fieldset key={q.id} className="space-y-3">
              <legend className="text-lg font-semibold leading-snug">
                <span className="tnum mr-2 text-ink-2">{i + 1}</span>
                {q.question}
              </legend>
              <p className="text-sm text-ink-2">
                {q.reason}{" "}
                {clause && (
                  <button
                    type="button"
                    onClick={() => onOpenClause(clause)}
                    className="tnum font-semibold text-ink underline decoration-1 underline-offset-4 hover:decoration-2"
                  >
                    Read {clauseRef(clause)}
                  </button>
                )}
              </p>
              {q.answer_kind === "choice" ? (
                <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={q.question}>
                  {[...(q.choices ?? []), DONT_KNOW].map((c) => (
                    <button
                      key={c}
                      type="button"
                      role="radio"
                      aria-checked={value === c}
                      onClick={() => set(c)}
                      className={clsx(
                        "h-10 border-2 px-4 text-sm font-semibold transition-colors",
                        value === c ? "border-ink bg-ink text-paper" : "border-ink/70 hover:border-ink",
                      )}
                    >
                      {c === DONT_KNOW ? "I don’t know" : c}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  <label htmlFor={`${q.id}-text`} className="sr-only">
                    {q.question}
                  </label>
                  <textarea
                    maxLength={4000}
                    id={`${q.id}-text`}
                    rows={2}
                    value={value === DONT_KNOW ? "" : value}
                    disabled={value === DONT_KNOW}
                    onChange={(e) => set(e.target.value)}
                    className="block w-full resize-y border-2 border-ink bg-paper px-3 py-2 placeholder:text-ink-2 focus:border-ink disabled:opacity-50"
                    placeholder="For example: customer ID and postcode, for churn modelling"
                  />
                  <label className="inline-flex items-center gap-2 text-sm font-medium">
                    <input
                      type="checkbox"
                      checked={value === DONT_KNOW}
                      onChange={(e) => set(e.target.checked ? DONT_KNOW : "")}
                      className="size-4 accent-[var(--ink)]"
                    />
                    I don&rsquo;t know
                  </label>
                </div>
              )}
            </fieldset>
          );
        })}
        <Button type="submit" variant="mark" size="lg" loading={submitting} disabled={!complete}>
          {localReview ? "Save confirmations" : "Answer"}
        </Button>
        {localReview && onFinishLocal && <div>
          <Button type="button" variant="outline" className="h-auto min-h-10 w-full whitespace-normal py-2" disabled={submitting} onClick={onFinishLocal}>Finish with remaining checks unknown</Button>
          <p className="mt-2 text-sm text-ink-2">Unsaved selections are left unknown. The report will withhold clearance while checks remain unknown.</p>
        </div>}
      </form>
    </section>
  );
}

export function Composer({
  disabled,
  hint,
  onSend,
  sending,
  onFocusChange,
}: {
  disabled: boolean;
  hint: string;
  onSend: (text: string) => Promise<void> | void;
  sending: boolean;
  onFocusChange?: (focused: boolean) => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);
  return (
    <form
      className="border-t-2 border-ink bg-paper p-4 md:p-5"
      onSubmit={async (e) => {
        e.preventDefault();
        if (disabled || sending || inFlight.current || !text.trim() || text.trim().length > 4000) return;
        inFlight.current = true;
        setError(null);
        try {
          await onSend(text.trim());
          setText("");
        } catch {
          setError("That did not send. Your text is still here; try again.");
        } finally {
          inFlight.current = false;
        }
      }}
    >
      <label htmlFor="composer" className="text-sm font-semibold">
        Add a detail or ask a follow-up
      </label>
      <div className="mt-2 flex items-end gap-2">
        <textarea
          id="composer"
          maxLength={4000}
          rows={2}
          value={text}
          disabled={disabled || sending}
          onChange={(e) => setText(e.target.value)}
          onFocus={() => onFocusChange?.(true)}
          onBlur={() => onFocusChange?.(false)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) e.currentTarget.form?.requestSubmit();
          }}
          className="block min-h-12 w-full resize-none border-2 border-ink bg-sheet px-3 py-2 placeholder:text-ink-2 focus:border-ink disabled:opacity-50"
          placeholder="The vendor review was approved in March"
          aria-describedby="composer-hint"
        />
        <Button type="submit" aria-label="Send" disabled={disabled || !text.trim()} loading={sending} size="icon">
          {!sending && <ArrowUp size={22} aria-hidden />}
        </Button>
      </div>
      <p id="composer-hint" className="mt-2 text-sm text-ink-2">
        {error ? <span className="text-violated">{error}</span> : hint}
      </p>
    </form>
  );
}
