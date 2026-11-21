// Composer state (spec 005): one reducer for everything the three steps edit, the step names, and the local draft
// (this browser, this user). Pure functions only, so the steps stay dumb and the draft logic is testable.
import type { Dispatch } from "react";

import { EMPTY_AUDIENCE, type AudienceDraft } from "./AudiencePicker";
import type { Block } from "@/lib/types";

import { newDraft, nextId, toBlocks, type Draft } from "./blocks";

export const STEPS = ["plantilla", "contenido", "envio"] as const;
export type Step = (typeof STEPS)[number];

export const STEP_LABEL: Record<Step, string> = {
  plantilla: "Plantilla",
  contenido: "Contenido",
  envio: "Destinatarios y envío",
};

/** An unknown or missing `?paso=` falls back to the first step. */
export function parseStep(value: string | null): Step {
  return STEPS.find((step) => step === value) ?? "plantilla";
}

/** Where the content came from: a template (built-in or saved) with the content's signature right after loading it,
 * so "unchanged" can be told later; or nothing ("blank", or an email reused from the history). */
export type TemplateOrigin = "blank" | { id: string | number; sig: string };

export interface ComposerState {
  template: TemplateOrigin;
  /** Step 3 "Guardar como plantilla" (checked by default) and its name; null follows the subject. */
  saveOnSend: boolean;
  templateName: string | null;
  subject: string;
  preheader: string;
  replyTo: string;
  drafts: Draft[];
  audience: AudienceDraft;
  /** "auto" follows the audience's club; null = the board; a number = that club (superadmin only). */
  sender: "auto" | null | number;
}

export type ComposerAction =
  | { type: "patch"; patch: Partial<ComposerState> }
  | { type: "defaultReplyTo"; value: string }
  | { type: "restore"; state: ComposerState }
  | { type: "reset"; state: ComposerState };

export function initialState(): ComposerState {
  return {
    template: "blank",
    saveOnSend: true,
    templateName: null,
    subject: "",
    preheader: "",
    replyTo: "",
    drafts: [newDraft("paragraph")],
    audience: EMPTY_AUDIENCE,
    sender: "auto",
  };
}

export function composerReducer(state: ComposerState, action: ComposerAction): ComposerState {
  switch (action.type) {
    case "patch":
      return { ...state, ...action.patch };
    case "defaultReplyTo":
      // The server's default only fills an empty field: anything typed before it arrives wins.
      return state.replyTo ? state : { ...state, replyTo: action.value };
    case "restore":
    case "reset":
      return action.state;
  }
}

/** Something worth keeping: the sender typed a subject, a preview text or at least one block with content. */
export function isDirty(state: ComposerState): boolean {
  return Boolean(state.subject.trim() || state.preheader.trim() || toBlocks(state.drafts).length > 0 || state.drafts.length > 1);
}

// ---- Local draft -----------------------------------------------------------------------------------------------
// One slot in localStorage, tagged with the user id. A slot that belongs to someone else is deleted on mount, which
// covers logout and shared computers without touching the auth provider.

export const DRAFT_KEY = "upiixsol.mail-draft";

export interface StoredDraft {
  userId: number;
  savedAt: number;
  state: ComposerState;
}

/** A draft saved before spec 006 held one audience kind; it has no `sources` and is dropped. */
function isDraftAudience(value: unknown): boolean {
  const a = value as Record<string, unknown> | null;
  return typeof a === "object" && a !== null && Array.isArray(a.sources) && Array.isArray(a.people) && Array.isArray(a.emails) && Array.isArray(a.excluded);
}

function isStoredDraft(value: unknown): value is StoredDraft {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  const state = v.state as Record<string, unknown> | null;
  return typeof v.userId === "number" && typeof v.savedAt === "number" && typeof state === "object" && state !== null && Array.isArray(state.drafts) && typeof state.subject === "string" && isDraftAudience(state.audience);
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(DRAFT_KEY);
  } catch {
    /* storage blocked: there is no draft to clear */
  }
}

export function saveDraft(userId: number, state: ComposerState): void {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ userId, savedAt: Date.now(), state } satisfies StoredDraft));
  } catch {
    /* storage full or blocked: the composer works without a draft */
  }
}

/** The signed-in user's draft, or null. Another user's (or an unreadable) draft is deleted. */
export function loadDraft(userId: number): StoredDraft | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (raw === null) return null;
    const parsed: unknown = JSON.parse(raw);
    if (isStoredDraft(parsed) && parsed.userId === userId) {
      // A draft from before the gallery has no template fields: they take their defaults.
      return { ...parsed, state: { ...initialState(), ...parsed.state } };
    }
  } catch {
    /* unreadable: treated as no draft */
  }
  clearDraft();
  return null;
}

// ---- Shared by the steps -------------------------------------------------------------------------------------

export const MAX_SUBJECT = 150;
export const MAX_PREHEADER = 140;
export const BOARD = "La mesa directiva de UpiixSol";

export interface StepProps {
  state: ComposerState;
  dispatch: Dispatch<ComposerAction>;
  /** Slug of the club the "Ver el club" button preset links to; null while none applies. */
  clubSlug: string | null;
  /** Slug that limits the campus-event picker; null = every club's events; undefined = not known yet. */
  eventsAcademy: string | null | undefined;
  /** What the exact preview renders; null while there is nothing to show. */
  previewPayload: object | null;
  onBack: () => void;
}

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

/** "1 de diciembre": the period end is a UTC midnight, so read it in UTC. */
export function renewal(iso: string) {
  const d = new Date(iso);
  return `${d.getUTCDate()} de ${MESES[d.getUTCMonth()]}`;
}

export function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}


// ---- Templates (spec 005 §Templates) --------------------------------------------------------------------------

export const MAX_TEMPLATE_NAME = 60;
export const MAX_TEMPLATE_DESCRIPTION = 140;

const localDateTime = (value: unknown) => (typeof value === "string" ? value.slice(0, 16) : "");
const str = (value: unknown) => (typeof value === "string" ? value : "");

/** Stored blocks back into editable drafts. A block the editor cannot read is dropped; an event slot
 * (`placeholder`) or an event without data becomes an empty campus event that asks to be completed. */
export function blocksToDrafts(blocks: ReadonlyArray<Block | Record<string, unknown>>): Draft[] {
  const drafts: Draft[] = [];
  for (const raw of blocks) {
    const b = raw as Record<string, unknown>;
    const id = nextId();
    switch (b.kind) {
      case "heading":
      case "paragraph":
        drafts.push({ id, kind: b.kind, text: str(b.text) });
        break;
      case "list":
        drafts.push({ id, kind: "list", text: Array.isArray(b.items) ? b.items.map(str).join("\n") : "", ordered: b.ordered === true });
        break;
      case "button":
        drafts.push({ id, kind: "button", label: str(b.label), url: str(b.url) });
        break;
      case "event": {
        const empty = { id, kind: "event" as const, eventTitle: "", coverUrl: null, title: "", start: "", end: "", place: "", description: "", link: "" };
        if (b.placeholder === true) drafts.push({ ...empty, mode: "campus", eventId: null });
        else if (typeof b.event_id === "number") drafts.push({ ...empty, mode: "campus", eventId: b.event_id });
        else {
          drafts.push({ ...empty, mode: "typed", eventId: null, title: str(b.title), start: localDateTime(b.start), end: localDateTime(b.end), place: str(b.place), description: str(b.description), link: str(b.link) });
        }
        break;
      }
      case "image":
        drafts.push({ id, kind: "image", url: str(b.url), alt: str(b.alt), link: str(b.link) });
        break;
      case "divider":
        drafts.push({ id, kind: "divider" });
        break;
    }
  }
  return drafts.length > 0 ? drafts : [newDraft("paragraph")];
}

/** What identifies the email's content, for "did it come unchanged from a template?". */
export function contentSignature(state: Pick<ComposerState, "subject" | "preheader" | "drafts">): string {
  return JSON.stringify([state.subject.trim(), state.preheader.trim(), toBlocks(state.drafts)]);
}

/** The state patch that loads a template or a sent email into the composer (never touches the audience). */
export function loadContent(content: { subject: string; preheader: string | null; blocks: ReadonlyArray<Block | Record<string, unknown>> }, origin: string | number | null): Partial<ComposerState> {
  const loaded = { subject: content.subject, preheader: content.preheader ?? "", drafts: blocksToDrafts(content.blocks) };
  return { ...loaded, template: origin === null ? "blank" : { id: origin, sig: contentSignature(loaded) }, saveOnSend: true, templateName: null };
}

/** The content is exactly what a template gave: nothing worth saving again. */
export function isUnchangedTemplate(state: ComposerState): boolean {
  return state.template !== "blank" && state.template.sig === contentSignature(state);
}

/** `name (2)` within the 60-character limit. */
export function numberedName(name: string, n: number): string {
  const suffix = ` (${n})`;
  return `${name.slice(0, MAX_TEMPLATE_NAME - suffix.length).trimEnd()}${suffix}`;
}
