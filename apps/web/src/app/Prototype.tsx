import { ButtonLink } from "@/components/Button";

/* Shown in live (http) mode for screens that only exist as fixture prototypes (plan §12). */
export function Prototype() {
  return (
    <div className="mx-auto max-w-[1600px] px-4 py-20 md:px-8">
      <h1 className="max-w-[18ch] font-display text-[clamp(2.5rem,5vw,4.5rem)] font-bold leading-[1.02]">
        Prototype screen.
      </h1>
      <p className="mt-4 max-w-[52ch] text-lg text-ink-2">
        This screen was designed with fixture data and is not connected to the live backend in this version.
        Cases, policies and questions are.
      </p>
      <ButtonLink to="/app/cases" variant="primary" size="lg" className="mt-8">
        Go to cases
      </ButtonLink>
    </div>
  );
}
