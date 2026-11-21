// Editable email blocks (spec 004). The composer keeps drafts (with a local id and raw text) and turns the
// complete ones into the API's `Block[]`; the same list feeds the live preview and the send.
import type { Block } from "@/lib/types";

export const MAX_BLOCKS = 30;
export const SITE_URL = "https://www.upiixsol.com";

export type DraftKind = "heading" | "paragraph" | "list" | "button" | "event" | "image" | "divider";

export type Draft = { id: string } & (
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; text: string; ordered: boolean } // text: one item per line
  | { kind: "button"; label: string; url: string }
  | {
      kind: "event";
      mode: "campus" | "typed";
      eventId: number | null; // campus mode: the picked event (the server reads it at send time)
      eventTitle: string; // campus mode: shown in the editor only
      coverUrl: string | null; // campus mode: the event's cover, offered to the image block
      title: string;
      start: string; // `datetime-local` value: America/Mexico_City, no offset
      end: string;
      place: string;
      description: string;
      link: string;
    }
  | { kind: "image"; url: string; alt: string; link: string }
  | { kind: "divider" }
);

/** What the canvas inserter offers: name and a one-line description. */
export const KINDS: { kind: DraftKind; label: string; hint: string }[] = [
  { kind: "heading", label: "Título", hint: "Un encabezado grande" },
  { kind: "paragraph", label: "Párrafo", hint: "Texto con negritas, cursivas y enlaces" },
  { kind: "list", label: "Lista", hint: "Con viñetas o numerada" },
  { kind: "button", label: "Botón", hint: "Un enlace destacado" },
  { kind: "event", label: "Evento", hint: "Tarjeta con fecha y calendario" },
  { kind: "image", label: "Imagen", hint: "Sube un cartel o una foto" },
  { kind: "divider", label: "Separador", hint: "Una línea entre dos partes" },
];

export const KIND_LABEL: Record<DraftKind, string> = {
  heading: "Título",
  paragraph: "Párrafo",
  list: "Lista",
  button: "Botón",
  event: "Evento",
  image: "Imagen",
  divider: "Separador",
};

// Ids only need to be unique within one email, but a restored draft (or a template) already carries ids from an
// earlier page load: a per-load prefix keeps new ones from colliding with them.
const LOAD = Math.random().toString(36).slice(2, 7);
let counter = 0;
export const nextId = () => `b${LOAD}${++counter}`;

export function newDraft(kind: DraftKind): Draft {
  const id = nextId();
  switch (kind) {
    case "heading":
    case "paragraph":
      return { id, kind, text: "" };
    case "list":
      return { id, kind, text: "", ordered: false };
    case "button":
      return { id, kind, label: "", url: "" };
    case "event":
      return { id, kind, mode: "campus", eventId: null, eventTitle: "", coverUrl: null, title: "", start: "", end: "", place: "", description: "", link: "" };
    case "image":
      return { id, kind, url: "", alt: "", link: "" };
    case "divider":
      return { id, kind };
  }
}

/** A copy of a block with its own id (the canvas "Duplicar"). */
export function duplicateDraft(draft: Draft): Draft {
  return { ...draft, id: nextId() };
}

/** `drafts` with the block at `from` moved to `to` (both indexes of the current list). */
export function moveDraft(drafts: Draft[], from: number, to: number): Draft[] {
  if (from === to || to < 0 || to >= drafts.length) return drafts;
  const next = [...drafts];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

export const isHttpUrl = (url: string) => /^https?:\/\/[^\s/?#]+[^\s]*$/i.test(url.trim());

/** What is missing in a block, in Spanish, shown next to it on the canvas (spec 004's rules); null when complete. */
export function blockProblem(draft: Draft): string | null {
  switch (draft.kind) {
    case "heading":
    case "paragraph":
      return draft.text.trim() ? null : "Escribe el texto o elimina el bloque.";
    case "list":
      return draft.text.trim() ? null : "Escribe al menos un elemento o elimina el bloque.";
    case "button":
      if (!draft.label.trim() || !draft.url.trim()) return "Falta el texto o el enlace del botón.";
      return isHttpUrl(draft.url) ? null : "El enlace debe empezar con http:// o https://";
    case "event":
      if (draft.mode === "campus") return draft.eventId === null ? "Elige un evento del calendario o escríbelo." : null;
      if (endBeforeStart(draft)) return "La hora de fin debe ser posterior a la de inicio.";
      return draft.title.trim() && draft.start && draft.end ? null : "Completa el título, el inicio y el fin del evento.";
    case "image":
      if (!draft.url) return "Sube una imagen o elimina el bloque.";
      return draft.alt.trim() ? null : "Escribe el texto alternativo de la imagen.";
    case "divider":
      return null;
  }
}

/** Typed events need an end after the start (both are `datetime-local` strings: they compare as text). */
export function endBeforeStart(draft: { start: string; end: string }): boolean {
  return Boolean(draft.start && draft.end && draft.end <= draft.start);
}

export function campusUrl() {
  return `${SITE_URL}/`;
}

export function clubUrl(slug: string) {
  return `${SITE_URL}/a/${slug}`;
}

/** A block with something to show: empty text, a list without items or a button without label and link are not. */
export function toBlock(draft: Draft): Block | null {
  switch (draft.kind) {
    case "heading":
    case "paragraph":
      return draft.text.trim() ? { kind: draft.kind, text: draft.text.trim() } : null;
    case "list": {
      const items = draft.text.split("\n").map((line) => line.trim()).filter(Boolean);
      return items.length ? { kind: "list", items, ordered: draft.ordered } : null;
    }
    case "button":
      return draft.label.trim() && draft.url.trim() ? { kind: "button", label: draft.label.trim(), url: draft.url.trim() } : null;
    case "event": {
      if (draft.mode === "campus") return draft.eventId === null ? null : { kind: "event", event_id: draft.eventId };
      if (!draft.title.trim() || !draft.start || !draft.end || endBeforeStart(draft)) return null;
      const optional = (value: string) => value.trim() || undefined;
      return {
        kind: "event",
        title: draft.title.trim(),
        start: draft.start,
        end: draft.end,
        place: optional(draft.place),
        description: optional(draft.description),
        link: optional(draft.link),
      };
    }
    case "image":
      return draft.url && draft.alt.trim() ? { kind: "image", url: draft.url, alt: draft.alt.trim(), ...(draft.link.trim() ? { link: draft.link.trim() } : {}) } : null;
    case "divider":
      return { kind: "divider" };
  }
}

export function toBlocks(drafts: Draft[]): Block[] {
  return drafts.flatMap((draft) => toBlock(draft) ?? []);
}

/** Blocks the sender started but did not finish (an untouched divider is always complete). */
export function incompleteCount(drafts: Draft[]): number {
  return drafts.filter((draft) => toBlock(draft) === null).length;
}
