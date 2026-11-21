// One block on the email canvas (spec 005 §Canvas): drawn with the renderer's sizes and the sender's theme, a
// toolbar while selected (format for text kinds, move, duplicate, delete), a drag handle and what is missing in
// Spanish right under it. Sizes mirror app/services/mail_render.py so the canvas and "Ver como llega" agree.
import {
  ArrowDown,
  ArrowUp,
  CalendarBlank,
  CopySimple,
  DotsSixVertical,
  Image as ImageIcon,
  LinkSimple,
  ListNumbers,
  TextB,
  TextItalic,
  Trash,
} from "@phosphor-icons/react";
import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type DragEvent, type KeyboardEvent, type ReactNode } from "react";

import type { MailCanvasTheme } from "@/lib/types";

import { isHttpUrl, KIND_LABEL, type Draft } from "./blocks";
import { Formatted, InlineText, insertLink, wrapSelection, type Edit } from "./InlineText";

const MONTHS = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"];

const tool = "grid size-9 place-items-center rounded-lg text-surface hover:bg-surface/15 focus-visible:outline-3 disabled:cursor-not-allowed disabled:opacity-40";

export type DragProps = {
  onDragStart: (event: DragEvent<HTMLElement>) => void;
  onDragEnd: () => void;
  onDragOver: (event: DragEvent<HTMLElement>) => void;
  onDrop: (event: DragEvent<HTMLElement>) => void;
  over: boolean;
  dragging: boolean;
};

function text(theme: MailCanvasTheme, size: number, line: number, extra: CSSProperties = {}): CSSProperties {
  return { fontFamily: theme.font, fontSize: size, lineHeight: `${line}px`, color: theme.colors.ink, ...extra };
}

function EventView({ draft, theme }: { draft: Extract<Draft, { kind: "event" }>; theme: MailCanvasTheme }) {
  const c = theme.colors;
  const typed = draft.mode === "typed";
  const title = typed ? draft.title.trim() : draft.eventTitle;
  const start = typed && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(draft.start) ? draft.start : null;
  return (
    <div style={{ background: c.tint, border: `1px solid ${c.line}`, borderRadius: 12, padding: 20 }} className="flex gap-4">
      <div style={{ background: c.secondary, color: c.on_secondary, borderRadius: 12, fontFamily: theme.font }} className="grid w-16 shrink-0 place-items-center self-start py-2 text-center">
        {start ? (
          <>
            <span style={{ fontSize: 11, lineHeight: "14px", fontWeight: 700 }}>{MONTHS[Number(start.slice(5, 7)) - 1]}</span>
            <span style={{ fontSize: 28, lineHeight: "32px", fontWeight: 800 }}>{Number(start.slice(8, 10))}</span>
          </>
        ) : (
          <CalendarBlank weight="bold" size={28} aria-hidden className="my-1.5" />
        )}
      </div>
      <div className="grid min-w-0 content-start gap-1" style={{ fontFamily: theme.font }}>
        <span style={text(theme, 18, 24, { fontWeight: 800, fontStyle: title ? "normal" : "italic" })} className="break-words">
          {title || (typed ? "Título del evento" : draft.eventId === null ? "Completa el evento" : "Evento del calendario")}
        </span>
        <span style={text(theme, 14, 22, { color: c.muted })}>
          {typed ? (start ? `${start.slice(11, 16)} h${draft.place.trim() ? ` · ${draft.place.trim()}` : ""}` : "Fecha y hora por definir") : draft.eventId === null ? "Elige uno del calendario o escríbelo: sin esto el correo no se envía." : "Del calendario del campus: la fecha y el lugar salen de ahí"}
        </span>
        {(typed || draft.eventId !== null) && <span style={text(theme, 14, 22, { color: c.link, fontWeight: 600 })}>Agregar a mi calendario</span>}
      </div>
    </div>
  );
}

/** The non-text blocks, as the email draws them. */
function StaticView({ draft, theme }: { draft: Draft; theme: MailCanvasTheme }) {
  const c = theme.colors;
  switch (draft.kind) {
    case "button":
      return (
        <span
          style={{ background: c.secondary, color: c.on_secondary, fontFamily: theme.font, fontSize: 16, lineHeight: "20px", fontWeight: 700, borderRadius: 10, padding: "14px 28px", opacity: draft.label.trim() ? 1 : 0.6 }}
          className="inline-block max-w-full break-words"
        >
          {draft.label.trim() || "Texto del botón"}
        </span>
      );
    case "image":
      return draft.url ? (
        <img src={draft.url} alt={draft.alt} className="block h-auto w-full" style={{ borderRadius: 12, maxWidth: 536 }} />
      ) : (
        <span style={{ borderColor: c.line, color: c.muted, borderRadius: 12, fontFamily: theme.font }} className="grid h-40 place-items-center gap-1 border-2 border-dashed text-sm">
          <span className="grid justify-items-center gap-1">
            <ImageIcon weight="bold" size={28} aria-hidden />
            Sube una imagen
          </span>
        </span>
      );
    case "divider":
      return <span aria-hidden className="block py-2"><span className="block h-px" style={{ background: c.line }} /></span>;
    case "event":
      return <EventView draft={draft} theme={theme} />;
    default:
      return null;
  }
}

/** Email paddings per kind (top, bottom), from the renderer. */
const PADDING: Record<Draft["kind"], [number, number]> = {
  heading: [8, 12],
  paragraph: [0, 16],
  list: [0, 16],
  button: [8, 24],
  event: [8, 24],
  image: [0, 20],
  divider: [8, 24],
};

export function CanvasBlock({
  draft,
  index,
  total,
  theme,
  selected,
  autoFocus,
  problem,
  canDuplicate,
  onSelect,
  onChange,
  onMove,
  onDuplicate,
  onDelete,
  onEnterInHeading,
  drag,
  after,
}: {
  draft: Draft;
  index: number;
  total: number;
  theme: MailCanvasTheme;
  selected: boolean;
  /** Focus this block's text (or the block) once: it was just inserted, moved or duplicated. */
  autoFocus: boolean;
  /** What is missing, shown under the block; null when complete or not yet worth saying. */
  problem: string | null;
  canDuplicate: boolean;
  onSelect: () => void;
  onChange: (next: Draft) => void;
  onMove: (by: -1 | 1) => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onEnterInHeading: () => void;
  drag: DragProps;
  /** The "+" on the seam under this block. */
  after: ReactNode;
}) {
  const input = useRef<HTMLTextAreaElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const problemId = useId();
  const [linking, setLinking] = useState<{ start: number; end: number } | null>(null);
  const [url, setUrl] = useState("https://");
  const [urlError, setUrlError] = useState<string | null>(null);
  const textKind = draft.kind === "heading" || draft.kind === "paragraph" || draft.kind === "list";
  const c = theme.colors;

  useEffect(() => {
    if (!autoFocus) return;
    if (input.current) {
      input.current.focus();
      input.current.setSelectionRange(input.current.value.length, input.current.value.length);
    } else if (draft.kind === "divider") box.current?.focus();
  }, [autoFocus, draft.kind]);

  // Leaving the block closes the link box (state adjusted during render, not in an effect).
  const [wasSelected, setWasSelected] = useState(selected);
  if (wasSelected !== selected) {
    setWasSelected(selected);
    if (!selected) setLinking(null);
  }

  // After a format or link edit, the textarea gets the new text on the next commit: restore focus and selection
  // right then (a layout effect), before any other input can land.
  const pendingSelection = useRef<Edit | null>(null);
  useLayoutEffect(() => {
    const edit = pendingSelection.current;
    if (!edit || !input.current || input.current.value !== edit.value) return;
    pendingSelection.current = null;
    input.current.focus();
    input.current.setSelectionRange(edit.start, edit.end);
  });

  function apply(edit: Edit) {
    if (!textKind) return;
    pendingSelection.current = edit;
    onChange({ ...draft, text: edit.value } as Draft);
  }

  function wrap(before: string, after: string) {
    const el = input.current;
    if (!el || !textKind) return;
    apply(wrapSelection(el.value, el.selectionStart, el.selectionEnd, before, after));
  }

  function openLink() {
    const el = input.current;
    if (!el) return;
    setLinking({ start: el.selectionStart, end: el.selectionEnd });
    setUrl("https://");
    setUrlError(null);
  }

  function applyLink() {
    const el = input.current;
    if (!el || !linking) return;
    if (!isHttpUrl(url)) return setUrlError("El enlace debe empezar con http:// o https://");
    setLinking(null);
    apply(insertLink(el.value, linking.start, linking.end, url));
  }

  function onTextKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    const mod = event.metaKey || event.ctrlKey;
    const key = event.key.toLowerCase();
    if (mod && !event.altKey && (key === "b" || key === "i" || key === "k")) {
      event.preventDefault();
      if (key === "k") openLink();
      else wrap(key === "b" ? "**" : "*", key === "b" ? "**" : "*");
    } else if (draft.kind === "heading" && event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onEnterInHeading();
    }
  }

  function onBlockKey(event: KeyboardEvent<HTMLLIElement>) {
    if (event.altKey && (event.key === "ArrowUp" || event.key === "ArrowDown")) {
      event.preventDefault();
      onMove(event.key === "ArrowUp" ? -1 : 1);
    }
  }

  const [top, bottom] = PADDING[draft.kind];
  const label = KIND_LABEL[draft.kind];
  const keep = (e: { preventDefault: () => void }) => e.preventDefault(); // toolbar clicks keep the text selection

  let content: ReactNode;
  if (draft.kind === "heading") {
    const style = text(theme, 26, 32, { fontWeight: 800, letterSpacing: "-0.3px" });
    content = (
      <>
        <InlineText
          inputRef={input}
          label="Texto del título"
          value={draft.text}
          onChange={(value) => onChange({ ...draft, text: value })}
          active={selected}
          placeholder="Escribe aquí el título"
          maxLength={120}
          singleLine
          textStyle={style}
          describedBy={problem ? problemId : undefined}
          onKeyDown={onTextKey}
          view={<h3 style={{ font: "inherit", margin: 0 }}><Formatted text={draft.text} linkColor={c.link} /></h3>}
        />
        <span aria-hidden className="mt-2.5 block h-1 w-12 rounded-sm" style={{ background: c.primary }} />
      </>
    );
  } else if (draft.kind === "paragraph") {
    content = (
      <InlineText
        inputRef={input}
        label="Texto del párrafo"
        value={draft.text}
        onChange={(value) => onChange({ ...draft, text: value })}
        active={selected}
        placeholder="Escribe aquí tu mensaje"
        maxLength={2000}
        textStyle={text(theme, 16, 26)}
        describedBy={problem ? problemId : undefined}
        onKeyDown={onTextKey}
        view={<Formatted text={draft.text} linkColor={c.link} />}
      />
    );
  } else if (draft.kind === "list") {
    const items = draft.text.split("\n").map((line) => line.trim()).filter(Boolean);
    const List = draft.ordered ? "ol" : "ul";
    content = (
      <InlineText
        inputRef={input}
        label="Elementos de la lista (uno por línea)"
        value={draft.text}
        onChange={(value) => onChange({ ...draft, text: value })}
        active={selected}
        placeholder="Un elemento por línea"
        textStyle={text(theme, 16, 26)}
        describedBy={problem ? problemId : undefined}
        onKeyDown={onTextKey}
        view={
          <List style={{ margin: 0, paddingLeft: 22, listStyleType: draft.ordered ? "decimal" : "disc", whiteSpace: "normal" }}>
            {items.map((item, i) => (
              <li key={i} style={{ margin: "0 0 8px", paddingLeft: 4 }}>
                <Formatted text={item} linkColor={c.link} />
              </li>
            ))}
          </List>
        }
      />
    );
  } else {
    content = (
      <div
        ref={box}
        tabIndex={0}
        role="button"
        aria-label={`Editar ${label.toLowerCase()}`}
        aria-describedby={problem ? problemId : undefined}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect();
          }
        }}
        className="cursor-pointer outline-none"
      >
        <StaticView draft={draft} theme={theme} />
      </div>
    );
  }

  return (
    <li
      aria-label={`Bloque ${index + 1}: ${label}`}
      data-block={draft.id}
      data-selected={selected || undefined}
      onFocus={(e) => !(e.target as HTMLElement).closest("[data-inserter]") && onSelect()}
      onMouseDown={(e) => {
        if (!selected && !(e.target as HTMLElement).closest("button,input,textarea,a,[data-inserter]")) onSelect();
      }}
      onKeyDown={onBlockKey}
      onDragOver={drag.onDragOver}
      onDrop={drag.onDrop}
      className={`group relative scroll-mt-32 px-3 sm:px-[calc(var(--gutter)-12px)] ${drag.dragging ? "opacity-50" : ""}`}
    >
      {drag.over && <span aria-hidden className="absolute inset-x-3 -top-0.5 z-10 h-1 rounded-full bg-primary" />}
      <span
        draggable
        aria-label="Arrastrar para mover"
        title="Arrastra para mover · Alt+↑/↓"
        onDragStart={drag.onDragStart}
        onDragEnd={drag.onDragEnd}
        className={`absolute top-1/2 left-0 hidden -translate-y-1/2 cursor-grab rounded p-0.5 text-muted active:cursor-grabbing sm:block ${selected ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}
      >
        <DotsSixVertical weight="bold" size={18} aria-hidden />
      </span>
      {selected && (
        <div role="toolbar" aria-label="Herramientas del bloque" onMouseDown={keep} className="absolute -top-11 left-2 z-20 flex items-center gap-0.5 rounded-xl bg-ink p-1 shadow-lift sm:left-[calc(var(--gutter)-12px)]">
          {textKind && (
            <>
              <button type="button" className={tool} aria-label="Negritas" title="Negritas (Ctrl+B)" onClick={() => wrap("**", "**")}>
                <TextB weight="bold" size={18} />
              </button>
              <button type="button" className={tool} aria-label="Cursivas" title="Cursivas (Ctrl+I)" onClick={() => wrap("*", "*")}>
                <TextItalic weight="bold" size={18} />
              </button>
              <button type="button" className={tool} aria-label="Enlace" title="Enlace (Ctrl+K)" aria-expanded={linking !== null} onClick={openLink}>
                <LinkSimple weight="bold" size={18} />
              </button>
              {draft.kind === "list" && (
                <button type="button" className={`${tool} ${draft.ordered ? "bg-surface/20" : ""}`} aria-label="Lista numerada" aria-pressed={draft.ordered} onClick={() => onChange({ ...draft, ordered: !draft.ordered })}>
                  <ListNumbers weight="bold" size={18} />
                </button>
              )}
              <span aria-hidden className="mx-1 h-5 w-px bg-surface/25" />
            </>
          )}
          <button type="button" className={tool} aria-label="Mover arriba" disabled={index === 0} onClick={() => onMove(-1)}>
            <ArrowUp weight="bold" size={18} />
          </button>
          <button type="button" className={tool} aria-label="Mover abajo" disabled={index === total - 1} onClick={() => onMove(1)}>
            <ArrowDown weight="bold" size={18} />
          </button>
          <button type="button" className={tool} aria-label="Duplicar bloque" disabled={!canDuplicate} title={canDuplicate ? undefined : draft.kind === "event" ? "Un correo lleva un solo evento" : "Un correo admite hasta 30 bloques."} onClick={onDuplicate}>
            <CopySimple weight="bold" size={18} />
          </button>
          <button type="button" className={tool} aria-label="Eliminar bloque" onClick={onDelete}>
            <Trash weight="bold" size={18} />
          </button>
        </div>
      )}
      <div
        className={`relative rounded-lg px-3 motion-safe:transition-shadow ${selected ? "ring-2 ring-primary" : problem ? "ring-1 ring-danger/60" : "group-hover:ring-1 group-hover:ring-line"}`}
        style={{ paddingTop: top, paddingBottom: bottom }}
      >
        {content}
        {selected && <span className="pointer-events-none absolute -bottom-2.5 right-2 rounded-full bg-primary px-2.5 py-0.5 text-xs font-bold text-on-primary">{label}</span>}
      </div>
      {linking && selected && (
        <div className="relative z-20 mx-3 mt-2 grid gap-2 rounded-xl border border-line bg-surface p-3 shadow-lift sm:flex sm:items-end">
          <label className="grid min-w-0 flex-1 gap-1 text-sm font-semibold">
            Dirección del enlace
            <input
              type="url"
              inputMode="url"
              autoFocus
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  applyLink();
                } else if (e.key === "Escape") {
                  e.preventDefault();
                  setLinking(null);
                  input.current?.focus();
                }
              }}
              aria-invalid={urlError !== null}
              className="min-h-11 rounded-xl border border-line bg-surface px-3 font-normal focus-visible:outline-3"
            />
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={applyLink} className="min-h-11 rounded-full bg-ink px-4 text-sm font-semibold text-surface focus-visible:outline-3">
              Aplicar enlace
            </button>
            <button type="button" onClick={() => { setLinking(null); input.current?.focus(); }} className="min-h-11 rounded-full px-4 text-sm font-semibold hover:bg-subtle focus-visible:outline-3">
              Cancelar
            </button>
          </div>
          {urlError && <p className="text-sm font-semibold text-danger sm:basis-full">{urlError}</p>}
        </div>
      )}
      {problem && (
        <p id={problemId} className="px-3 pt-1 pb-2 text-sm font-semibold text-danger" style={{ fontFamily: theme.font }}>
          {problem}
        </p>
      )}
      <div data-inserter className={`absolute -bottom-4 left-1/2 z-10 -translate-x-1/2 ${selected ? "opacity-100" : "opacity-0 group-hover:opacity-100 focus-within:opacity-100"}`}>{after}</div>
    </li>
  );
}
