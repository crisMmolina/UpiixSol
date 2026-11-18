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

/** What the "Agregar" row offers. */
export const KINDS: { kind: DraftKind; label: string }[] = [
  { kind: "heading", label: "Título" },
  { kind: "paragraph", label: "Párrafo" },
  { kind: "list", label: "Lista" },
  { kind: "button", label: "Botón" },
  { kind: "event", label: "Evento" },
  { kind: "image", label: "Imagen" },
  { kind: "divider", label: "Separador" },
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

let counter = 0;
const nextId = () => `b${++counter}`;

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
