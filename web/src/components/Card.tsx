import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Lift on hover (clickable cards). */
  interactive?: boolean;
  /** Colored top stripe with the academy primary color. */
  stripe?: boolean;
}

export function Card({ interactive = false, stripe = false, className = "", children, ...props }: CardProps) {
  return (
    <div
      className={
        "relative overflow-hidden rounded-card border border-line bg-surface shadow-soft " +
        (interactive ? "transition hover:-translate-y-0.5 hover:shadow-lift " : "") +
        className
      }
      {...props}
    >
      {stripe && <div aria-hidden className="h-1.5 w-full bg-primary" />}
      {children}
    </div>
  );
}

export function SectionTitle({ title, action, subtitle }: { title: string; action?: ReactNode; subtitle?: string }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h2 className="text-2xl">{title}</h2>
        {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
