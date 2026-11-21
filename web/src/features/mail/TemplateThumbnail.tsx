// A live thumbnail of a template: the server's render-only preview (no audience), in a scaled, fully sandboxed
// iframe. Renders are cached per content for the page's life, so going back and forth costs nothing.
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { PreviewOut } from "@/lib/types";

const EMAIL_WIDTH = 600;
const EMAIL_HEIGHT = 900;
const cache = new Map<string, Promise<string>>();

function render(key: string, payload: object): Promise<string> {
  let hit = cache.get(key);
  if (!hit) {
    hit = api<PreviewOut>("/mail/preview", { method: "POST", json: payload }).then((out) => out.html);
    hit.catch(() => cache.delete(key)); // a failure is retried next time
    cache.set(key, hit);
  }
  return hit;
}

/** A wireframe, for while the render loads or when it fails. */
export function Wireframe() {
  return (
    <span aria-hidden className="grid h-full content-start gap-3 rounded-xl border border-line bg-surface p-5">
      <span className="h-1.5 w-full rounded-full bg-primary" />
      <span className="mx-auto mt-2 h-4 w-24 rounded-full bg-primary/60" />
      <span className="mt-3 h-4 w-3/4 rounded-full bg-line" />
      <span className="h-2.5 w-full rounded-full bg-subtle" />
      <span className="h-2.5 w-11/12 rounded-full bg-subtle" />
      <span className="h-2.5 w-2/3 rounded-full bg-subtle" />
      <span className="mt-2 h-8 w-28 rounded-full border-2 border-dashed border-line" />
    </span>
  );
}

export function TemplateThumbnail({ name, subject, preheader, blocks }: { name: string; subject: string; preheader: string | null; blocks: unknown[] }) {
  const box = useRef<HTMLSpanElement>(null);
  const [scale, setScale] = useState(0.4);
  const [html, setHtml] = useState<string | null>(null);
  const payload = { subject, blocks, ...(preheader ? { preheader } : {}) };
  const key = JSON.stringify(payload);

  useEffect(() => {
    const node = box.current;
    if (!node) return;
    const watcher = new ResizeObserver(([entry]) => entry && setScale(entry.contentRect.width / EMAIL_WIDTH));
    watcher.observe(node);
    return () => watcher.disconnect();
  }, []);

  useEffect(() => {
    let current = true;
    render(key, JSON.parse(key) as object)
      .then((out) => current && setHtml(out))
      .catch(() => current && setHtml(null));
    return () => {
      current = false;
    };
  }, [key]);

  return (
    <span ref={box} className="relative block aspect-[3/4] w-full overflow-hidden rounded-xl border border-line bg-white">
      {html === null ? (
        <Wireframe />
      ) : (
        <iframe
          title={`Miniatura de ${name}`}
          sandbox=""
          srcDoc={html}
          tabIndex={-1}
          scrolling="no"
          style={{ width: EMAIL_WIDTH, height: EMAIL_HEIGHT, transform: `scale(${scale})` }}
          className="pointer-events-none absolute top-0 left-0 origin-top-left border-0"
        />
      )}
    </span>
  );
}
