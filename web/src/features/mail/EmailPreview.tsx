// Live preview (spec 004 §Preview): the exact HTML the server renders, in a sandboxed iframe, 400 ms after the
// last change. The iframe is sandboxed WITHOUT `allow-scripts`: nothing in the email can run code. It gets
// `allow-same-origin` only so the page can read the document's height and fit the frame to it (no inner
// scroll, the footer is never cut); without scripts that grants the email no capabilities (plan.md §STRIDE).
import { useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { PreviewOut } from "@/lib/types";

const DEBOUNCE_MS = 400;
const WIDTHS = { desktop: 600, phone: 375 } as const;
type Mode = keyof typeof WIDTHS;

const toggle = "inline-flex min-h-11 items-center rounded-full px-4 text-sm font-semibold transition focus-visible:outline-3";

/** Keeps an iframe as tall as its document, also when images load later or the width changes. */
function useFitHeight(deps: unknown[]) {
  const ref = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState<number | null>(null);
  const [observer, setObserver] = useState<ResizeObserver | null>(null);

  useEffect(() => {
    const watcher = new ResizeObserver(([entry]) => entry && setHeight(Math.ceil(entry.target.scrollHeight)));
    setObserver(watcher);
    return () => watcher.disconnect();
  }, []);

  function attach() {
    const doc = ref.current?.contentDocument;
    if (!doc?.documentElement || !observer) return;
    observer.disconnect();
    observer.observe(doc.documentElement);
    setHeight(Math.ceil(doc.documentElement.scrollHeight));
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(attach, [observer, ...deps]);
  return { ref, height, onLoad: attach };
}

export function EmailPreview({ payload, emptyHint }: { payload: object | null; emptyHint: string }) {
  const [mode, setMode] = useState<Mode>(() => (typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches ? "phone" : "desktop"));
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = payload ? JSON.stringify(payload) : null;
  const fit = useFitHeight([html, mode]);

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
      {html === null ? (
        <p className="grid h-48 place-items-center rounded-2xl border border-dashed border-line px-4 text-center text-sm text-muted">{key === null ? emptyHint : "Generando vista previa…"}</p>
      ) : (
        <iframe
          title="Vista previa del correo"
          ref={fit.ref}
          onLoad={fit.onLoad}
          sandbox="allow-same-origin"
          srcDoc={html}
          scrolling="no"
          style={{ width: WIDTHS[mode], height: fit.height ?? 640 }}
          className="mx-auto block max-w-full overflow-hidden rounded-2xl border border-line bg-white"
        />
      )}
    </section>
  );
}
