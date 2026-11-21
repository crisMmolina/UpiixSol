// The email canvas of step 2 (spec 005 §Canvas, plan.md §Design): a React mirror of the email, styled with the
// `theme` the preview endpoint returns for this sender (colors, logo, "Enviado por", font, 600 px), where the sender
// clicks a block to edit it, inserts with "+", reorders by dragging or Alt+↑/↓, duplicates and deletes with a 5 s
// undo. Typing is local; the exact server render is "Ver como llega". Buttons, events and images open
// `BlockProperties` (side panel on desktop, bottom sheet on phones).
import { useEffect, useMemo, useRef, useState, type DragEvent } from "react";

import { api } from "@/lib/api";
import { useSite } from "@/lib/brand";
import type { MailCanvasTheme, PreviewOut } from "@/lib/types";

import { reorderIds } from "../academy-admin/sortable";
import { BlockInserter } from "./BlockInserter";
import { BlockProperties, HAS_PROPERTIES } from "./BlockProperties";
import { CanvasBlock } from "./CanvasBlock";
import { blockProblem, duplicateDraft, MAX_BLOCKS, moveDraft, newDraft, type Draft, type DraftKind } from "./blocks";

const UNDO_MS = 5000;

// ---- Theme ----------------------------------------------------------------------------------------------------
// One render-only preview per sender gives the theme (the server's own values); typing never refetches it.
const themes = new Map<string, Promise<MailCanvasTheme | null>>();

function useCanvasTheme(previewPayload: object | null): MailCanvasTheme {
  const site = useSite();
  const sender = (previewPayload as { sender_academy_id?: number } | null)?.sender_academy_id ?? null;
  const key = String(sender);
  const [theme, setTheme] = useState<MailCanvasTheme | null>(null);

  useEffect(() => {
    let current = true;
    if (!themes.has(key)) {
      const json = { subject: "Sin asunto", blocks: [{ kind: "divider" }], ...(sender === null ? {} : { sender_academy_id: sender }) };
      themes.set(
        key,
        api<PreviewOut>("/mail/preview", { method: "POST", json })
          .then((out) => out.theme ?? null)
          .catch(() => {
            themes.delete(key); // try again next time
            return null;
          }),
      );
    }
    void themes.get(key)?.then((value) => current && value && setTheme(value));
    return () => {
      current = false;
    };
  }, [key, sender]);

  // Until the server answers (a moment): the site's colors on the app's tokens.
  return useMemo(
    () =>
      theme ?? {
        site_name: site.name,
        site_logo_url: null,
        colors: {
          primary: site.colors.primary,
          secondary: site.colors.secondary,
          accent: site.colors.accent,
          ink: "var(--color-ink)",
          muted: "var(--color-muted)",
          page: "var(--color-subtle)",
          card: "var(--color-surface)",
          tint: "var(--color-subtle)",
          line: "var(--color-line)",
          link: "var(--color-link)",
          on_secondary: "var(--color-on-primary)",
        },
        font: "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif",
        spacing: { width: 600, gutter: 32, radius: 16 },
        sender: { label: "Enviado por la mesa directiva de", name: site.name, logo_url: null },
      },
    [theme, site],
  );
}

/** Desktop (side panel) or phone (bottom sheet), following the layout's `lg` breakpoint. */
function useWide(): boolean {
  const query = "(min-width: 1024px)";
  const [wide, setWide] = useState(() => typeof window !== "undefined" && window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setWide(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return wide;
}

// ---- Frame ----------------------------------------------------------------------------------------------------

function Logo({ url, name, height, theme }: { url: string | null; name: string; height: number; theme: MailCanvasTheme }) {
  return url ? (
    <img src={url} alt={name} style={{ height }} className="mx-auto block w-auto max-w-full" />
  ) : (
    <span style={{ fontFamily: theme.font, fontSize: height / 2 + 4, lineHeight: `${height}px`, fontWeight: 800, color: theme.colors.link }} className="break-words">
      {name}
    </span>
  );
}

function SenderLine({ theme }: { theme: MailCanvasTheme }) {
  const { sender, colors } = theme;
  const label = { fontFamily: theme.font, fontSize: 14, lineHeight: "20px", color: colors.ink };
  const club = sender.label === "Enviado por";
  return (
    <div className="px-5 pt-5 pb-6 text-center sm:px-(--gutter)" style={{ borderBottom: `1px solid ${colors.line}` }}>
      {club ? (
        <>
          <div style={label} className="pb-2">
            {sender.label}
          </div>
          <Logo url={sender.logo_url} name={sender.name} height={36} theme={theme} />
        </>
      ) : (
        <div style={label}>
          {sender.label} <strong>{sender.name}</strong>
        </div>
      )}
    </div>
  );
}

// ---- Canvas ---------------------------------------------------------------------------------------------------

export function EmailCanvas({
  drafts,
  onChange,
  clubSlug,
  eventsAcademy,
  previewPayload,
}: {
  drafts: Draft[];
  onChange: (next: Draft[]) => void;
  clubSlug: string | null;
  eventsAcademy: string | null | undefined;
  previewPayload: object | null;
}) {
  const theme = useCanvasTheme(previewPayload);
  const wide = useWide();
  const root = useRef<HTMLDivElement>(null);
  const endInserter = useRef<HTMLDivElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [undo, setUndo] = useState<{ draft: Draft; index: number } | null>(null);
  const [said, setSaid] = useState("");
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);

  const full = drafts.length >= MAX_BLOCKS;
  const eventTaken = drafts.some((d) => d.kind === "event");
  const selected = drafts.find((d) => d.id === selectedId) ?? null;
  const picked = drafts.find((d) => d.kind === "event");
  const cover = picked?.kind === "event" && picked.mode === "campus" ? picked.coverUrl : null;
  const c = theme.colors;

  // A focus request is consumed by the children's effects in the same commit.
  useEffect(() => {
    if (focusId !== null) setFocusId(null);
  }, [focusId]);

  // The undo notice leaves after 5 s; the block stays deleted.
  useEffect(() => {
    if (!undo) return;
    const timer = window.setTimeout(() => setUndo(null), UNDO_MS);
    return () => window.clearTimeout(timer);
  }, [undo]);

  function select(id: string | null) {
    if (selectedId !== null && selectedId !== id) setTouched((seen) => new Set(seen).add(selectedId));
    setSelectedId(id);
  }

  // Clicking or tabbing anywhere outside the canvas and its panel ends the editing.
  const selectRef = useRef(select);
  useEffect(() => {
    selectRef.current = select;
  });
  useEffect(() => {
    const away = (event: Event) => {
      const target = event.target as Node | null;
      if (target && target !== document.body && !root.current?.contains(target)) selectRef.current(null);
    };
    document.addEventListener("pointerdown", away);
    document.addEventListener("focusin", away);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("focusin", away);
    };
  }, []);

  function focusAndSelect(id: string) {
    select(id);
    setFocusId(id);
  }

  function insert(index: number, kind: DraftKind) {
    if (full || (kind === "event" && eventTaken)) return;
    const draft = newDraft(kind);
    onChange([...drafts.slice(0, index), draft, ...drafts.slice(index)]);
    focusAndSelect(draft.id);
  }

  function update(next: Draft) {
    onChange(drafts.map((d) => (d.id === next.id ? next : d)));
  }

  function move(index: number, to: number) {
    if (to < 0 || to >= drafts.length || to === index) return;
    const id = drafts[index].id;
    onChange(moveDraft(drafts, index, to));
    focusAndSelect(id);
    setSaid(`Bloque movido a la posición ${to + 1} de ${drafts.length}.`);
  }

  function duplicate(index: number) {
    const source = drafts[index];
    if (full || source.kind === "event") return;
    const copy = duplicateDraft(source);
    onChange([...drafts.slice(0, index + 1), copy, ...drafts.slice(index + 1)]);
    focusAndSelect(copy.id);
  }

  function remove(index: number) {
    const draft = drafts[index];
    onChange(drafts.filter((_, i) => i !== index));
    setUndo({ draft, index });
    setSelectedId(null);
    // Focus stays in the canvas: the next block, or "+" at the end.
    const next = drafts[index + 1] ?? drafts[index - 1];
    if (next) setFocusId(next.id);
    else requestAnimationFrame(() => endInserter.current?.querySelector("button")?.focus());
  }

  function restore() {
    if (!undo || drafts.length >= MAX_BLOCKS) return;
    const at = Math.min(undo.index, drafts.length);
    onChange([...drafts.slice(0, at), undo.draft, ...drafts.slice(at)]);
    setUndo(null);
    focusAndSelect(undo.draft.id);
  }

  function dragProps(index: number) {
    return {
      dragging: dragFrom === index,
      over: dragFrom !== null && over === index && dragFrom !== index,
      onDragStart(event: DragEvent<HTMLElement>) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", drafts[index].id); // Firefox needs data to start a drag
        setDragFrom(index);
      },
      onDragEnd() {
        setDragFrom(null);
        setOver(null);
      },
      onDragOver(event: DragEvent<HTMLElement>) {
        if (dragFrom === null) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        if (over !== index) setOver(index);
      },
      onDrop(event: DragEvent<HTMLElement>) {
        if (dragFrom === null) return;
        event.preventDefault();
        const from = dragFrom;
        setDragFrom(null);
        setOver(null);
        if (from === index) return;
        // sortable.ts orders numeric ids: the indexes of the current list.
        const order = reorderIds(drafts.map((_, i) => i), from, index);
        onChange(order.map((i) => drafts[i]));
        focusAndSelect(drafts[from].id);
        setSaid(`Bloque movido a la posición ${order.indexOf(from) + 1} de ${drafts.length}.`);
      },
    };
  }

  const problemOf = (draft: Draft) => (draft.id !== selectedId && touched.has(draft.id) ? blockProblem(draft) : null);
  const sheetOpen = !wide && selected !== null && HAS_PROPERTIES.has(selected.kind);

  return (
    <div ref={root} className={`grid items-start gap-6 ${wide ? "grid-cols-[minmax(0,1fr)_19rem]" : ""}`}>
      <section aria-label="Lienzo del correo" className="-mx-5 grid gap-4 px-2 py-6 sm:mx-0 sm:rounded-2xl sm:px-8 sm:py-8" style={{ background: c.page }}>
        <div
          data-testid="email-card"
          className="mx-auto w-full"
          style={{
            maxWidth: theme.spacing.width,
            fontFamily: theme.font,
            color: c.ink,
            background: c.card,
            border: `1px solid ${c.line}`,
            borderRadius: theme.spacing.radius,
            ["--gutter" as string]: `${theme.spacing.gutter}px`,
          }}
        >
          <div aria-hidden style={{ height: 6, background: c.primary, borderRadius: `${theme.spacing.radius}px ${theme.spacing.radius}px 0 0` }} />
          <div className="px-5 pt-7 pb-5 text-center sm:px-(--gutter)">
            <Logo url={theme.site_logo_url} name={theme.site_name} height={48} theme={theme} />
          </div>
          <SenderLine theme={theme} />
          <p className="px-5 pt-6 pb-3 sm:px-(--gutter)" style={{ fontSize: 15, lineHeight: "22px", color: c.muted }}>
            Hola, <span style={{ background: c.tint, border: `1px dashed ${c.line}`, borderRadius: 6 }} className="px-1.5">nombre de quien lo recibe</span>
          </p>
          <ol aria-label="Bloques del correo" className="grid pt-1">
            {drafts.map((draft, index) => (
              <CanvasBlock
                key={draft.id}
                draft={draft}
                index={index}
                total={drafts.length}
                theme={theme}
                selected={draft.id === selectedId}
                autoFocus={draft.id === focusId}
                problem={problemOf(draft)}
                canDuplicate={!full && draft.kind !== "event"}
                onSelect={() => draft.id !== selectedId && select(draft.id)}
                onChange={update}
                onMove={(by) => move(index, index + by)}
                onDuplicate={() => duplicate(index)}
                onDelete={() => remove(index)}
                onEnterInHeading={() => insert(index + 1, "paragraph")}
                drag={dragProps(index)}
                after={
                  index < drafts.length - 1 && (
                    <BlockInserter variant="between" label={`Insertar bloque después del bloque ${index + 1}`} disabled={full} eventTaken={eventTaken} onPick={(kind) => insert(index + 1, kind)} />
                  )
                }
              />
            ))}
          </ol>
          <div ref={endInserter} className="px-5 pt-2 pb-6 sm:px-(--gutter)">
            {drafts.length === 0 && <p className="pb-3 text-center text-sm" style={{ color: c.muted }}>El correo está vacío. Agrega el primer bloque.</p>}
            <BlockInserter variant="end" label="Agregar bloque al final" disabled={full} eventTaken={eventTaken} onPick={(kind) => insert(drafts.length, kind)} />
            {full && <p className="pt-2 text-center text-sm font-semibold" style={{ color: c.muted }}>{`Un correo admite hasta ${MAX_BLOCKS} bloques.`}</p>}
          </div>
          <div className="px-5 py-6 sm:px-(--gutter)" style={{ background: c.tint, borderTop: `1px solid ${c.line}`, borderRadius: `0 0 ${theme.spacing.radius}px ${theme.spacing.radius}px`, fontSize: 12, lineHeight: "18px", color: c.muted }}>
            <p style={{ fontWeight: 700, color: c.ink }} className="pb-2">
              {theme.sender.label === "Enviado por" ? `Enviado por ${theme.sender.name}` : `Enviado por la mesa directiva de ${theme.sender.name}`}
            </p>
            <p>
              <span className="underline">Darte de baja</span> · <span className="underline">{theme.site_name}</span>
            </p>
          </div>
        </div>
      </section>
      <BlockProperties
        draft={selected}
        wide={wide}
        autoFocus={selected !== null && selected.id === focusId}
        onClose={() => select(null)}
        onDuplicate={() => selected && duplicate(drafts.indexOf(selected))}
        onDelete={() => selected && remove(drafts.indexOf(selected))}
        canDuplicate={!full && selected?.kind !== "event"}
        problem={selected && touched.has(selected.id) ? blockProblem(selected) : null}
        onChange={update}
        clubSlug={clubSlug}
        eventsAcademy={eventsAcademy}
        cover={cover}
      />
      {sheetOpen && <div aria-hidden className="h-[45dvh]" />}
      <p role="status" className="sr-only">
        {said}
      </p>
      {undo && (
        <div role="status" className="fixed bottom-24 left-1/2 z-50 flex lg:bottom-6 -translate-x-1/2 items-center gap-3 rounded-full bg-ink py-1.5 pr-1.5 pl-5 text-sm text-surface shadow-lift">
          Bloque eliminado
          <button type="button" onClick={restore} className="min-h-10 rounded-full px-4 font-semibold text-surface underline-offset-2 hover:bg-surface/15 focus-visible:outline-3">
            Deshacer
          </button>
        </div>
      )}
    </div>
  );
}
