// Live preview (spec 004 §Preview): the exact HTML the server renders, in a sandboxed iframe, 400 ms after the
// last change. `sandbox=""` (no scripts, no same-origin) is the security boundary (plan.md §STRIDE).
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { PreviewOut } from "@/lib/types";

const DEBOUNCE_MS = 400;
const WIDTHS = { desktop: 600, phone: 375 } as const;
type Mode = keyof typeof WIDTHS;

const toggle = "inline-flex min-h-11 items-center rounded-full px-4 text-sm font-semibold transition focus-visible:outline-3";

export function EmailPreview({ payload, emptyHint }: { payload: object | null; emptyHint: string }) {
  const [mode, setMode] = useState<Mode>(() => (typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches ? "phone" : "desktop"));
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = payload ? JSON.stringify(payload) : null;

  useEffect(() => {
    if (key === null) {
      setHtml(null);
      setError(null);
      return;
    }
    let current = true;
    const timer = window.setTimeout(() => {
      api<PreviewOut>("/mail/preview", { method: "POST", json: JSON.parse(key) })
        .then((out) => {
          if (!current) return;
          setHtml(out.html);
          setError(null);
        })
        .catch((err) => current && setError(errorMessage(err)));
    }, DEBOUNCE_MS);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [key]);

  return (
    <section aria-label="Vista previa" className="grid content-start gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Vista previa</h3>
        <div role="group" aria-label="Ancho de la vista previa" className="flex rounded-full border border-line p-0.5">
          {(["desktop", "phone"] as const).map((m) => (
            <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)} className={`${toggle} ${mode === m ? "bg-ink text-surface" : "text-ink hover:bg-subtle"}`}>
              {m === "desktop" ? "Escritorio" : "Teléfono"}
            </button>
          ))}
        </div>
      </div>
      {error && (
        <p role="alert" className="text-sm font-semibold text-danger">
          {error}
        </p>
      )}
      <div className="overflow-x-auto rounded-2xl border border-line bg-subtle p-3">
        {html === null && !error && key === null ? (
          <p className="grid h-40 place-items-center text-center text-sm text-muted">{emptyHint}</p>
        ) : (
          <iframe
            title="Vista previa del correo"
            sandbox=""
            srcDoc={html ?? ""}
            style={{ width: WIDTHS[mode] }}
            className="mx-auto block h-[34rem] max-w-none rounded-lg border-0 bg-white"
          />
        )}
      </div>
    </section>
  );
}
