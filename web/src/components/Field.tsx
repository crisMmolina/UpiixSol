import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

const control =
  "w-full rounded-[var(--radius-field)] border border-line bg-surface px-3.5 py-2.5 text-ink shadow-xs " +
  "placeholder:text-muted/70 focus:border-secondary focus:outline-none focus:ring-3 focus:ring-primary/25 " +
  "aria-invalid:border-accent-2 aria-invalid:ring-accent-2/20 disabled:bg-bg";

interface FieldShellProps {
  label: string;
  hint?: string;
  error?: string;
  children: (props: { id: string; describedBy?: string; invalid: boolean }) => ReactNode;
}

function FieldShell({ label, hint, error, children }: FieldShellProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {label}
      </label>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {hint && !error && (
        <p id={hintId} className="text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs font-semibold text-accent-2">
          {error}
        </p>
      )}
    </div>
  );
}

type Common = { label: string; hint?: string; error?: string };

export function TextField({ label, hint, error, className = "", ...props }: Common & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <FieldShell label={label} hint={hint} error={error}>
      {({ id, describedBy, invalid }) => (
        <input id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={`${control} ${className}`} {...props} />
      )}
    </FieldShell>
  );
}

export function TextArea({ label, hint, error, className = "", ...props }: Common & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <FieldShell label={label} hint={hint} error={error}>
      {({ id, describedBy, invalid }) => (
        <textarea id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={`${control} min-h-28 ${className}`} {...props} />
      )}
    </FieldShell>
  );
}

export function SelectField({ label, hint, error, className = "", children, ...props }: Common & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <FieldShell label={label} hint={hint} error={error}>
      {({ id, describedBy, invalid }) => (
        <select id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={`${control} ${className}`} {...props}>
          {children}
        </select>
      )}
    </FieldShell>
  );
}

/** Field errors from a 422 response (`details[].loc` → message), keyed by the last loc segment. */
export function fieldErrors(details: unknown): Record<string, string> {
  if (!Array.isArray(details)) return {};
  const errors: Record<string, string> = {};
  for (const item of details as { loc?: unknown[]; msg?: string }[]) {
    const key = item.loc?.at(-1);
    if (typeof key === "string" && item.msg) errors[key] ??= item.msg.replace(/^Value error, /, "");
  }
  return errors;
}
