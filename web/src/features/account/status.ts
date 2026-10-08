// One status line per tab: a new result replaces the previous one instead of piling up (audit auth.md 4).
import { useState, type Dispatch, type SetStateAction } from "react";

import { fieldErrors } from "@/components/Field";
import { ApiError, errorMessage } from "@/lib/api";

export type Status = { source: string; tone: "success" | "error"; text: string } | null;
export type SetStatus = Dispatch<SetStateAction<Status>>;
export type Errors = Record<string, string>;

/** The tab's shared status, as seen by one form (`source`). */
export function statusFor(status: Status, source: string): Status {
  return status?.source === source ? status : null;
}

/**
 * Runs one form's request. Field errors (already in Spanish, see fieldErrors) go under the fields the
 * form shows; the result or any other error becomes the tab's single status line.
 */
export function useFormRequest(source: string, fields: readonly string[], setStatus: SetStatus) {
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Errors>({});

  /** Local checks failed: mark the fields and drop this form's stale status. */
  function reject(local: Errors) {
    setErrors(local);
    setStatus((current) => (current?.source === source ? null : current));
  }

  async function run(request: () => Promise<string>) {
    setBusy(true);
    setErrors({});
    setStatus(null);
    try {
      const text = await request();
      setStatus({ source, tone: "success", text });
    } catch (error) {
      const all = error instanceof ApiError ? fieldErrors(error.details) : {};
      const shown = Object.fromEntries(Object.entries(all).filter(([field]) => fields.includes(field)));
      setErrors(shown);
      const text = Object.keys(shown).length ? "Revisa los campos marcados." : errorMessage(error);
      setStatus({ source, tone: "error", text });
    } finally {
      setBusy(false);
    }
  }

  /** Editing a field clears its error and this form's old result. */
  function edited(field: string) {
    setErrors((current) => {
      if (!(field in current)) return current;
      const { [field]: _cleared, ...rest } = current;
      return rest;
    });
    setStatus((current) => (current?.source === source ? null : current));
  }

  return { busy, errors, reject, run, edited };
}
