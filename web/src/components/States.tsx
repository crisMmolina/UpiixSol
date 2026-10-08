import { WarningCircle } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import { Button } from "./Button";

/** Empty state with the mascot of the current club (or UpiixSol's) and an optional action. */
export function EmptyState({
  title,
  description,
  action,
  mascotUrl = "/brand/upiixsol/mascot.png",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  mascotUrl?: string | null;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card border border-dashed border-line bg-surface px-6 py-12 text-center">
      {mascotUrl && <img src={mascotUrl} alt="" className="h-28 w-auto object-contain" loading="lazy" />}
      <h3 className="text-xl">{title}</h3>
      {description && <p className="max-w-md text-muted">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-card border border-accent-2/30 bg-surface px-6 py-8 text-center">
      <WarningCircle size={36} weight="bold" className="text-accent-2" aria-hidden />
      <p className="max-w-md text-ink">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  );
}

/** Inline banner (e.g. "cambia tu contraseña"). */
export function Notice({ children, action, tone = "accent" }: { children: ReactNode; action?: ReactNode; tone?: "accent" | "alert" }) {
  return (
    <div
      role="status"
      className={`flex flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-medium ${
        tone === "alert" ? "bg-accent-2 text-white" : "bg-accent/20 text-ink ring-1 ring-accent/50"
      }`}
    >
      <span>{children}</span>
      {action}
    </div>
  );
}
