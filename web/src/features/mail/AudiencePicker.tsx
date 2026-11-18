// Audience picker (spec 003): everyone, one club, one role or specific people (campus users + outside addresses).
import { MagnifyingGlass, Plus, X } from "@phosphor-icons/react";
import { useEffect, useId, useState } from "react";

import { Button } from "@/components/Button";
import { SelectField, TextArea, TextField } from "@/components/Field";
import { api, errorMessage } from "@/lib/api";
import type { Audience, MailStatus, Page, Role } from "@/lib/types";

export const MAX_ENTRIES = 50;
/** Outside addresses have no per-campaign cap; only the monthly quota limits them (UPS-097). */
const COLLAPSE_AFTER = 8;

export type AudienceKind = Audience["kind"];

/** A campus user as the picker shows it (no email unless the API sent it, which is superadmins only). */
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
  kind: AudienceKind;
  academyId: number | null;
  role: Role;
  people: Person[];
  emails: string[];
}

export const EMPTY_AUDIENCE: AudienceDraft = { kind: "all", academyId: null, role: "member", people: [], emails: [] };

export const KIND_LABEL: Record<AudienceKind, string> = {
  all: "Todo UpiixSol",
  academy: "Un club",
  role: "Un rol",
  individual: "Personas",
};

export const ROLE_LABEL: Record<Role, string> = {
  superadmin: "Superadmin",
  academy_admin: "Admin de club",
  member: "Miembro",
};

/** The API body for a draft, or null while it is incomplete. */
export function toAudience(draft: AudienceDraft): Audience | null {
  switch (draft.kind) {
    case "all":
      return { kind: "all" };
    case "academy":
      return draft.academyId ? { kind: "academy", academy_id: draft.academyId } : null;
    case "role":
      return { kind: "role", role: draft.role };
    case "individual":
      return draft.people.length + draft.emails.length > 0
        ? { kind: "individual", user_ids: draft.people.map((p) => p.id), emails: draft.emails }
        : null;
  }
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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

function PersonSearch({ draft, onChange }: { draft: AudienceDraft; onChange: (next: AudienceDraft) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Person[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | undefined>();
  const [pasted, setPasted] = useState("");
  const [report, setReport] = useState<PasteResult | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [remaining, setRemaining] = useState<number | null>(null);
  const full = draft.people.length >= MAX_ENTRIES;
  const collapsed = draft.emails.length > COLLAPSE_AFTER && !showAll;

  useEffect(() => {
    api<MailStatus>("/mail/status")
      .then((status) => setRemaining(status.remaining))
      .catch(() => setRemaining(null));
  }, []);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults(null);
      return;
    }
    let live = true;
    const timer = window.setTimeout(() => {
      api<Page<Person>>("/mail/recipients", { query: { q, limit: 8 } })
        .then((page) => {
          if (!live) return;
          setResults(page.items);
          setError(null);
        })
        .catch((err) => live && setError(errorMessage(err)));
    }, 250);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, [query]);

  function addPerson(person: Person) {
    if (full || draft.people.some((p) => p.id === person.id)) return;
    onChange({ ...draft, people: [...draft.people, person] });
  }

  function addEmail() {
    const value = email.trim().toLowerCase();
    if (!EMAIL.test(value)) return setEmailError("Escribe un correo válido.");
    if (draft.emails.includes(value)) return setEmailError("Ese correo ya está en la lista.");
    onChange({ ...draft, emails: [...draft.emails, value] });
    setEmail("");
    setEmailError(undefined);
  }

  function addPasted() {
    const result = parsePaste(pasted, draft.emails);
    if (result.added.length > 0) onChange({ ...draft, emails: [...draft.emails, ...result.added] });
    setReport(result);
    setPasted(result.invalid.join("\n"));
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-2">
        <TextField
          label="Buscar personas por nombre o apodo"
          type="search"
          value={query}
          autoComplete="off"
          onChange={(e) => setQuery(e.target.value)}
          error={error ?? undefined}
          hint="Escribe al menos 2 letras."
        />
        {results && (
          <ul className="grid gap-1" aria-label="Resultados">
            {results.length === 0 && <li className="text-sm text-muted">Sin resultados.</li>}
            {results.map((person) => {
              const added = draft.people.some((p) => p.id === person.id);
              return (
                <li key={person.id}>
                  <button
                    type="button"
                    aria-label={`Agregar ${person.full_name}`}
                    disabled={added || full}
                    onClick={() => addPerson(person)}
                    className="flex min-h-11 w-full items-center gap-2 rounded-2xl border border-line bg-surface px-3 text-left text-sm hover:bg-subtle disabled:opacity-50"
                  >
                    <MagnifyingGlass size={16} weight="bold" aria-hidden className="shrink-0 text-muted" />
                    <span className="font-semibold">{person.full_name}</span>
                    <span className="text-muted">@{person.nickname}</span>
                    {added && <span className="ml-auto text-xs text-muted">Agregada</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <form
        noValidate
        className="flex flex-wrap items-start gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          addEmail();
        }}
      >
        <div className="min-w-0 flex-1 basis-56">
          <TextField
            label="Correo externo"
            type="email"
            value={email}
            autoComplete="off"
            onChange={(e) => {
              setEmail(e.target.value);
              setEmailError(undefined);
            }}
            error={emailError}
            reserve
          />
        </div>
        <Button type="submit" variant="secondary" icon={<Plus weight="bold" />} className="mt-[1.65rem]">
          Agregar correo
        </Button>
      </form>

      <div className="grid gap-2">
        <TextArea
          label="Pegar varios correos"
          value={pasted}
          autoComplete="off"
          spellCheck={false}
          rows={4}
          onChange={(e) => setPasted(e.target.value)}
          hint="Pega una lista de Gmail, Outlook o una hoja de cálculo: separados por comas, espacios o renglones. También sirve «Nombre <correo@x.com>»."
        />
        <div>
          <Button type="button" variant="secondary" icon={<Plus weight="bold" />} disabled={!pasted.trim()} onClick={addPasted}>
            Agregar todos
          </Button>
        </div>
        {report && (
          <p role="status" className="text-sm font-semibold">
            {`Se agregaron ${report.added.length} · ${report.repeated} repetidos · ${report.invalid.length} inválidos`}
          </p>
        )}
        {report && report.invalid.length > 0 && (
          <p className="break-words text-sm text-danger">{`Revisa estos y corrígelos en el cuadro: ${report.invalid.join(", ")}`}</p>
        )}
      </div>

      <p className="text-sm text-muted">
        <span>{`Personas ${draft.people.length}/${MAX_ENTRIES}`}</span> · <span>{`Correos externos ${draft.emails.length}`}</span>
      </p>
      {remaining !== null && draft.people.length + draft.emails.length > remaining && (
        <p role="alert" className="text-sm font-semibold text-danger">
          {`Supera tu cupo de este mes (${remaining.toLocaleString("en-US")} envíos). Quita algunos correos.`}
        </p>
      )}

      {draft.people.length > 0 && (
        <ul className="flex flex-wrap gap-2" aria-label="Personas elegidas">
          {draft.people.map((p) => (
            <Chip key={`u${p.id}`} label={p.full_name} remove={`Quitar a ${p.full_name}`} onRemove={() => onChange({ ...draft, people: draft.people.filter((x) => x.id !== p.id) })} />
          ))}
        </ul>
      )}

      {draft.emails.length > COLLAPSE_AFTER && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold">{`${draft.emails.length} correos externos`}</span>
          <Button type="button" variant="secondary" onClick={() => setShowAll((v) => !v)} aria-expanded={showAll}>
            {showAll ? "Ocultar" : "Ver todos"}
          </Button>
          <Button type="button" variant="secondary" onClick={() => { onChange({ ...draft, emails: [] }); setShowAll(false); }}>
            Quitar todos
          </Button>
        </div>
      )}
      {draft.emails.length > 0 && !collapsed && (
        <ul className="flex max-h-72 flex-wrap gap-2 overflow-y-auto" aria-label="Correos externos elegidos">
          {draft.emails.map((address) => (
            <Chip key={address} label={address} remove={`Quitar ${address}`} onRemove={() => onChange({ ...draft, emails: draft.emails.filter((x) => x !== address) })} />
          ))}
        </ul>
      )}
    </div>
  );
}

function Chip({ label, remove, onRemove }: { label: string; remove: string; onRemove: () => void }) {
  return (
    <li className="inline-flex max-w-full items-center gap-1 rounded-full bg-subtle py-1 pl-3 pr-1 text-sm ring-1 ring-line">
      <span className="min-w-0 truncate">{label}</span>
      <button type="button" aria-label={remove} onClick={onRemove} className="grid size-9 place-items-center rounded-full hover:bg-line/60">
        <X size={14} weight="bold" aria-hidden />
      </button>
    </li>
  );
}

export function AudiencePicker({
  draft,
  onChange,
  academies,
  kinds = ["all", "academy", "role", "individual"],
  ownClub,
}: {
  draft: AudienceDraft;
  onChange: (next: AudienceDraft) => void;
  academies: AcademyChoice[];
  kinds?: AudienceKind[];
  /** A club admin's own club: the "academy" choice is labelled "Mi club" and needs no select. */
  ownClub?: boolean;
}) {
  const group = useId();
  return (
    <fieldset className="grid gap-4">
      <legend className="mb-2 text-sm font-semibold">Destinatarios</legend>
      <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
        {kinds.map((kind) => (
          <label
            key={kind}
            className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-full border px-4 text-sm font-semibold has-[:focus-visible]:outline-3 ${draft.kind === kind ? "border-primary bg-primary/10" : "border-line bg-surface hover:bg-subtle"}`}
          >
            <input type="radio" name={group} checked={draft.kind === kind} onChange={() => onChange({ ...draft, kind, academyId: kind === "academy" && ownClub ? (academies[0]?.id ?? null) : draft.academyId })} className="size-4 accent-[var(--color-link)]" />
            {kind === "academy" && ownClub ? "Mi club" : KIND_LABEL[kind]}
          </label>
        ))}
      </div>
      {draft.kind === "academy" && !ownClub && (
        <SelectField label="Club" value={draft.academyId ?? ""} onChange={(e) => onChange({ ...draft, academyId: e.target.value ? Number(e.target.value) : null })}>
          <option value="">Elige un club</option>
          {academies.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </SelectField>
      )}
      {draft.kind === "role" && (
        <SelectField label="Rol" value={draft.role} onChange={(e) => onChange({ ...draft, role: e.target.value as Role })}>
          {(Object.keys(ROLE_LABEL) as Role[]).map((role) => (
            <option key={role} value={role}>
              {ROLE_LABEL[role]}
            </option>
          ))}
        </SelectField>
      )}
      {draft.kind === "individual" && <PersonSearch draft={draft} onChange={onChange} />}
    </fieldset>
  );
}
