// Audience picker (spec 003): everyone, one club, one role or specific people (campus users + outside addresses).
import { MagnifyingGlass, Plus, X } from "@phosphor-icons/react";
import { useEffect, useId, useState } from "react";

import { Button } from "@/components/Button";
import { SelectField, TextField } from "@/components/Field";
import { api, errorMessage } from "@/lib/api";
import type { Audience, Page, Role } from "@/lib/types";

export const MAX_ENTRIES = 50;
export const MAX_OUTSIDE = 20;

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

function PersonSearch({ draft, onChange }: { draft: AudienceDraft; onChange: (next: AudienceDraft) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Person[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | undefined>();
  const total = draft.people.length + draft.emails.length;
  const full = total >= MAX_ENTRIES;

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
    if (draft.emails.length >= MAX_OUTSIDE) return setEmailError(`Máximo ${MAX_OUTSIDE} correos externos.`);
    if (full) return setEmailError(`Máximo ${MAX_ENTRIES} destinatarios en total.`);
    onChange({ ...draft, emails: [...draft.emails, value] });
    setEmail("");
    setEmailError(undefined);
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

      <p className="text-sm text-muted">
        <span>{`Personas ${total}/${MAX_ENTRIES}`}</span> · <span>{`Correos externos ${draft.emails.length}/${MAX_OUTSIDE}`}</span>
      </p>

      {total > 0 && (
        <ul className="flex flex-wrap gap-2" aria-label="Destinatarios elegidos">
          {draft.people.map((p) => (
            <Chip key={`u${p.id}`} label={p.full_name} remove={`Quitar a ${p.full_name}`} onRemove={() => onChange({ ...draft, people: draft.people.filter((x) => x.id !== p.id) })} />
          ))}
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
}: {
  draft: AudienceDraft;
  onChange: (next: AudienceDraft) => void;
  academies: AcademyChoice[];
  kinds?: AudienceKind[];
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
            <input type="radio" name={group} checked={draft.kind === kind} onChange={() => onChange({ ...draft, kind })} className="size-4 accent-[var(--color-link)]" />
            {KIND_LABEL[kind]}
          </label>
        ))}
      </div>
      {draft.kind === "academy" && (
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
