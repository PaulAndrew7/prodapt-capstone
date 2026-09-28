import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/Button";
import { ErrorNotice } from "@/components/Feedback";
import { todayIso } from "@/lib/format";
import { VENDOR_SCENARIO } from "@/fixtures/vendorCase";

const AREAS = ["Marketing analytics", "Claims", "Technology", "Pricing", "Procurement", "Sales", "Other"];

const SAMPLES = [
  { label: "Share data with a new vendor", text: VENDOR_SCENARIO, area: "Marketing analytics" },
  {
    label: "Contractor production access",
    text: "A contractor from Fenwick Systems needs production database access for three weeks to finish a migration.",
    area: "Technology",
  },
  {
    label: "Client dinner at a new venue",
    text: "Can I host a client dinner at a restaurant we have not used before?",
    area: "Sales",
  },
];

/* The entry point for every case: describe the activity, then Assess. */
export function ScenarioComposer({ headingLevel = "h1" }: { headingLevel?: "h1" | "h2" }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [area, setArea] = useState(AREAS[0]);
  const [asOf, setAsOf] = useState(todayIso());
  const [touched, setTouched] = useState(false);
  const inFlight = useRef(false);
  const create = useMutation({
    mutationFn: () => api.createCase({ text: text.trim(), business_area: area, as_of: asOf }),
    onSuccess: (c) => {
      void qc.invalidateQueries({ queryKey: ["cases"] });
      navigate(`/app/cases/${c.id}?run=start`);
    },
  });
  const tooShort = text.trim().length < 20;
  const tooLong = text.trim().length > 4000;
  const parsedDate = new Date(`${asOf}T00:00:00Z`);
  const validDate = /^\d{4}-\d{2}-\d{2}$/.test(asOf) && Number(asOf.slice(0, 4)) > 0
    && Number.isFinite(parsedDate.getTime()) && parsedDate.toISOString().slice(0, 10) === asOf;
  const submit = async () => {
    setTouched(true);
    if (tooShort || tooLong || !validDate || create.isPending || inFlight.current) return;
    inFlight.current = true;
    try {
      await create.mutateAsync();
    } catch {
      // The mutation error is rendered below; preserve the form for a validated retry.
    } finally {
      inFlight.current = false;
    }
  };
  const H = headingLevel;

  return (
    <div className="grid gap-x-16 gap-y-10 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
        noValidate
      >
        <H className="max-w-[18ch] font-display text-[clamp(2.5rem,5vw,4.75rem)] font-bold leading-[1.02] tracking-[-0.01em]">
          Describe what you&rsquo;re planning to do.
        </H>
        <p className="mt-4 max-w-[54ch] text-lg text-ink-2">
          Write it the way you would explain it to a colleague. Say what you don&rsquo;t know; Clause keeps unknowns
          visible instead of guessing.
        </p>

        <div className="mt-8 space-y-2">
          <label htmlFor="scenario" className="font-semibold">
            Scenario
          </label>
          <textarea
            id="scenario"
            maxLength={4000}
            rows={5}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) e.currentTarget.form?.requestSubmit();
            }}
            aria-invalid={touched && (tooShort || tooLong)}
            aria-describedby="scenario-help scenario-error"
            className="block w-full resize-y border-2 border-ink bg-sheet px-4 py-3 text-lg leading-relaxed placeholder:text-ink-2 focus:outline-2 focus:outline-offset-2 focus:outline-ink"
            placeholder="We want to send customer records to a new analytics vendor..."
          />
          <p id="scenario-help" className="text-sm text-ink-2">
            Name who, what data or money, and any approvals you already have.
          </p>
          {touched && tooShort && (
            <p id="scenario-error" className="text-sm font-semibold text-violated">
              Add a little more detail (at least 20 characters) so the right policies can be found.
            </p>
          )}
          {touched && tooLong && (
            <p id="scenario-error" className="text-sm font-semibold text-violated">
              Keep the scenario within 4,000 characters.
            </p>
          )}
        </div>

        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <label htmlFor="area" className="font-semibold">
              Business area
            </label>
            <select
              id="area"
              value={area}
              onChange={(e) => setArea(e.target.value)}
              className="block h-12 w-full border-2 border-ink bg-sheet px-3"
            >
              {AREAS.map((a) => (
                <option key={a}>{a}</option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label htmlFor="asof" className="font-semibold">
              Assess as of
            </label>
            <input
              id="asof"
              type="date"
              required
              aria-invalid={touched && !validDate}
              value={asOf}
              onChange={(e) => setAsOf(e.target.value)}
              className="tnum block h-12 w-full border-2 border-ink bg-sheet px-3"
              aria-describedby={touched && !validDate ? "asof-help asof-error" : "asof-help"}
            />
            <p id="asof-help" className="text-sm text-ink-2">
              Policies in force on this date are used.
            </p>
            {touched && !validDate && (
              <p id="asof-error" className="text-sm font-semibold text-violated">Choose a valid assessment date.</p>
            )}
          </div>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Button type="submit" variant="mark" size="lg" loading={create.isPending}>
            Assess
          </Button>
          <span className="text-sm text-ink-2">Ctrl+Enter also works.</span>
        </div>
        {create.isError && (
          <div className="mt-6">
            <ErrorNotice
              title="The case was not created"
              body="Your scenario is still here. Try again."
              onRetry={() => { void submit(); }}
            />
          </div>
        )}
      </form>

      <aside aria-labelledby="samples-h" className="lg:pt-3">
        <h2 id="samples-h" className="font-semibold">
          Start from a sample
        </h2>
        <ul className="mt-3 divide-y divide-rule border-y-2 border-ink">
          {SAMPLES.map((s) => (
            <li key={s.label}>
              <button
                type="button"
                onClick={() => {
                  setText(s.text);
                  setArea(s.area);
                  document.getElementById("scenario")?.focus();
                }}
                className="w-full py-3 text-left hover:bg-mark hover:text-on-mark focus-visible:bg-mark focus-visible:text-on-mark"
              >
                <span className="block font-semibold">{s.label}</span>
                <span className="mt-0.5 line-clamp-2 block text-sm opacity-80">{s.text}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-sm text-ink-2">Samples use the fictional Kestrel Mutual policies.</p>
      </aside>
    </div>
  );
}

export function NewCase() {
  return (
    <div className="mx-auto max-w-[1600px] px-4 py-10 md:px-8 md:py-14">
      <ScenarioComposer />
    </div>
  );
}
