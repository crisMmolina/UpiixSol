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
        "relative overflow-hidden rounded-card border border-line bg-surface " +
        (interactive
          ? "transition duration-200 ease-out hover:-translate-y-0.5 hover:border-transparent hover:shadow-lift active:translate-y-0 "
          : "") +
        className
      }
      {...props}
    >
      {/* Absolute so it never becomes a grid/flex cell of the card's own layout. */}
      {stripe && <div aria-hidden className="absolute inset-x-0 top-0 h-1.5 bg-primary" />}
      {children}
    </div>
  );
}

export function SectionTitle({ title, action, subtitle }: { title: string; action?: ReactNode; subtitle?: string }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h2 className="text-xl sm:text-2xl">{title}</h2>
        {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
      </div>
      {/* Touch target ≥ 44 px for the link (UPS-040), the text looks the same. */}
      {action && <div className="[&>a]:inline-flex [&>a]:min-h-11 [&>a]:items-center [&>a]:font-semibold">{action}</div>}
    </div>
  );
}
