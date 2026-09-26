import { ButtonLink } from "@/components/Button";
import { Wordmark } from "@/components/Wordmark";

export function NotFound({ inApp = false }: { inApp?: boolean }) {
  return (
    <div className={inApp ? "mx-auto max-w-[1600px] px-4 py-20 md:px-8" : "min-h-dvh bg-paper px-4 py-10 md:px-8"}>
      {!inApp && <Wordmark />}
      <h1 className="mt-16 max-w-[16ch] font-display text-[clamp(2.75rem,6vw,5.5rem)] font-bold leading-[1.02]">
        No clause here.
      </h1>
      <p className="mt-4 max-w-[48ch] text-lg text-ink-2">This page does not exist, or the link is out of date.</p>
      <ButtonLink to="/app" variant="primary" size="lg" className="mt-8">
        Go to the overview
      </ButtonLink>
    </div>
  );
}
