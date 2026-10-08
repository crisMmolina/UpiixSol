import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

import { FormMessage } from "./FormMessage";

const control =
  "w-full rounded-[var(--radius-field)] border border-line bg-surface px-3.5 py-2.5 text-ink shadow-xs " +
  "placeholder:text-muted/70 focus:border-secondary focus:outline-none focus:ring-3 focus:ring-primary/25 " +
  "aria-invalid:border-accent-2 aria-invalid:ring-accent-2/20 disabled:bg-bg";

interface FieldShellProps {
  label: string;
  hint?: string;
  error?: string;
  /** Keep the message line even with no hint (no layout shift when an error shows up). */
  reserve?: boolean;
  children: (props: { id: string; describedBy?: string; invalid: boolean }) => ReactNode;
}

function FieldShell({ label, hint, error, reserve, children }: FieldShellProps) {
  const id = useId();
  const messageId = `${id}-message`;
  const describedBy = hint || error ? messageId : undefined;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {label}
      </label>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {(reserve || hint || error) && <FormMessage id={messageId} size="xs" live={false} message={error} hint={hint} />}
    </div>
  );
}

type Common = { label: string; hint?: string; error?: string; reserve?: boolean };

export function TextField({ label, hint, error, reserve, className = "", ...props }: Common & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <FieldShell label={label} hint={hint} error={error} reserve={reserve}>
      {({ id, describedBy, invalid }) => (
        <input id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={`${control} ${className}`} {...props} />
      )}
    </FieldShell>
  );
}

export function TextArea({ label, hint, error, reserve, className = "", ...props }: Common & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <FieldShell label={label} hint={hint} error={error} reserve={reserve}>
      {({ id, describedBy, invalid }) => (
        <textarea id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={`${control} min-h-28 ${className}`} {...props} />
      )}
    </FieldShell>
  );
}

export function SelectField({ label, hint, error, reserve, className = "", children, ...props }: Common & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <FieldShell label={label} hint={hint} error={error} reserve={reserve}>
      {({ id, describedBy, invalid }) => (
        <select id={id} aria-describedby={describedBy} aria-invalid={invalid || undefined} className={`${control} ${className}`} {...props}>
          {children}
        </select>
      )}
    </FieldShell>
  );
}

/** Spanish text for a pydantic validator error (the API sends `type` and the English `msg`, never `ctx`). */
function friendlyMessage(type: string | undefined, msg: string): string {
  const number = msg.match(/(-?\d+(?:\.\d+)?)/)?.[1];
  switch (type) {
    case undefined: // the API's own field errors are already in Spanish
      return msg;
    case "value_error":
      if (/valid email/i.test(msg)) return "Escribe un correo válido, como nombre@dominio.com.";
      return msg.startsWith("Value error, ") ? msg.slice("Value error, ".length) : "Revisa este campo.";
    case "missing":
      return "Este campo es obligatorio.";
    case "string_too_short":
    case "too_short":
      return number && number !== "1" ? `Usa al menos ${number} caracteres.` : "Este campo es obligatorio.";
    case "string_too_long":
    case "too_long":
      return number ? `Usa como máximo ${number} caracteres.` : "El texto es demasiado largo.";
    case "string_pattern_mismatch":
      return "El formato no es válido.";
    case "greater_than":
    case "greater_than_equal":
      return number ? `Debe ser al menos ${number}.` : "El valor es muy pequeño.";
    case "less_than":
    case "less_than_equal":
      return number ? `Debe ser como máximo ${number}.` : "El valor es muy grande.";
    case "int_parsing":
    case "int_type":
    case "float_parsing":
    case "float_type":
      return "Escribe un número válido.";
    case "literal_error":
    case "enum":
      return "Elige una de las opciones.";
    case "url_parsing":
    case "url_scheme":
    case "url_type":
      return "Escribe un enlace válido que empiece con https://.";
    case "date_parsing":
    case "date_from_datetime_parsing":
    case "datetime_parsing":
    case "datetime_from_date_parsing":
      return "Escribe una fecha válida.";
    case "extra_forbidden":
      return "Este dato no se puede cambiar aquí.";
    default:
      return "Revisa este campo.";
  }
}

/** Field errors from a 422 response (`details[].loc` → message), keyed by the last loc segment.
 *  Validator messages come back in Spanish (never "String should have at least 2 characters"). */
export function fieldErrors(details: unknown): Record<string, string> {
  if (!Array.isArray(details)) return {};
  const errors: Record<string, string> = {};
  for (const item of details as { loc?: unknown[]; msg?: string; type?: string }[]) {
    const key = item.loc?.at(-1);
    if (typeof key === "string" && item.msg) errors[key] ??= friendlyMessage(item.type, item.msg);
  }
  return errors;
}
