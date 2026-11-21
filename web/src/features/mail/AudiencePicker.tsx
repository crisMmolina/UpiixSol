// Audience helpers (spec 003, spec 006): the step-3 draft is always a combined (`mix`) audience: symbolic sources
// (everyone, a club, a role), picked people, outside addresses and the people the sender unchecked.
import { X } from "@phosphor-icons/react";

import type { Audience, AudienceSource, MixAudience, Role } from "@/lib/types";

export type AudienceKind = Audience["kind"];

/** A campus user as the person search shows it. */
export interface Person {
  id: number;
  full_name: string;
  nickname: string;
  avatar_url: string | null;
}

export interface AcademyChoice {
  id: number;
  name: string;
}

export interface AudienceDraft {
  sources: AudienceSource[];
  people: Person[];
  emails: string[];
  /** Users a source includes that the sender unchecked. */
  excluded: number[];
}

export const EMPTY_AUDIENCE: AudienceDraft = { sources: [], people: [], emails: [], excluded: [] };

export const KIND_LABEL: Record<AudienceKind, string> = {
  all: "Todo UpiixSol",
  academy: "Un club",
  role: "Un rol",
  individual: "Personas",
  mix: "Combinado",
};

export const ROLE_LABEL: Record<Role, string> = {
  superadmin: "Superadmin",
  academy_admin: "Admin de club",
  member: "Miembro",
};

/** The API body for a draft, or null while nothing was added. */
export function toAudience(draft: AudienceDraft): MixAudience | null {
  if (draft.sources.length + draft.people.length + draft.emails.length === 0) return null;
  return {
    kind: "mix",
    sources: draft.sources,
    user_ids: draft.people.map((p) => p.id),
    exclude_user_ids: draft.excluded,
    emails: draft.emails,
  };
}

export function sourceKey(source: AudienceSource): string {
  return source.kind === "all" ? "all" : source.kind === "academy" ? `academy:${source.academy_id}` : `role:${source.role}`;
}

export function sourceLabel(source: AudienceSource, academies: readonly AcademyChoice[], ownClub?: boolean): string {
  if (source.kind === "all") return "Todo UpiixSol";
  if (source.kind === "role") return `Rol: ${ROLE_LABEL[source.role]}`;
  if (ownClub) return "Mi club";
  return `Club ${academies.find((a) => a.id === source.academy_id)?.name ?? source.academy_id}`;
}

export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export interface PasteResult {
  added: string[];
  repeated: number;
  invalid: string[];
}

/** Addresses in a pasted block: commas, semicolons, spaces, tabs, new lines, `Nombre <correo>` and `mailto:`. */
export function parsePaste(text: string, existing: readonly string[]): PasteResult {
  const spaced = text.replace(/(?:"[^"]*"|[^<>,;\n]*)<([^<>]*)>/g, (_m, address: string) => `\n${address}\n`);
  const seen = new Set(existing);
  const result: PasteResult = { added: [], repeated: 0, invalid: [] };
  for (const raw of spaced.split(/[\s,;]+/)) {
    const token = raw.replace(/^mailto:/i, "").replace(/^["'([]+|["')\].]+$/g, "");
    if (!token) continue;
    const address = token.toLowerCase();
    if (!EMAIL.test(address)) result.invalid.push(raw);
    else if (seen.has(address)) result.repeated += 1;
    else {
      seen.add(address);
      result.added.push(address);
    }
  }
  return result;
}

export function Chip({ label, remove, onRemove }: { label: string; remove: string; onRemove: () => void }) {
  return (
    <li className="inline-flex max-w-full items-center gap-1 rounded-full bg-subtle py-1 pl-3 pr-1 text-sm ring-1 ring-line">
      <span className="min-w-0 truncate">{label}</span>
      <button type="button" aria-label={remove} onClick={onRemove} className="grid size-9 place-items-center rounded-full hover:bg-line/60">
        <X size={14} weight="bold" aria-hidden />
      </button>
    </li>
  );
}
