import type { ReactNode } from "react";
import { WarningOctagon } from "@phosphor-icons/react";
import clsx from "clsx";
import { Button } from "./Button";

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={clsx("bg-rule/70 motion-safe:animate-pulse", className)} />;
}

export function EmptyState({
  title,
  body,
  action,
  className,
}: {
  title: string;
  body: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("py-16", className)}>
      <p className="font-display text-3xl font-bold leading-tight">{title}</p>
      <p className="mt-3 max-w-[52ch] text-ink-2">{body}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

export function ErrorNotice({
  title,
  body,
  onRetry,
  requestId,
}: {
  title: string;
  body: string;
  onRetry?: () => void;
  requestId?: string;
}) {
  return (
    <div role="alert" className="flex items-start gap-4 border-2 border-violated bg-sheet p-5">
      <WarningOctagon size={24} className="mt-0.5 shrink-0 text-violated" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{title}</p>
        <p className="mt-1 text-ink-2">{body}</p>
        {requestId && <p className="tnum mt-2 text-sm text-ink-2">Request {requestId}</p>}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
