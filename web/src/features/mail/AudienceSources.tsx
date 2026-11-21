// Step 3 sources (spec 006): "Agregar destinatarios" menu and one removable chip per source with its count.
// Everyone / a club / a role are symbolic (the server re-resolves them at send time); people and outside
// addresses are listed one by one in the recipient list below.
import { CaretDown, MagnifyingGlass, Plus } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { Button, buttonClasses } from "@/components/Button";
import { TextArea, TextField } from "@/components/Field";
import { api, errorMessage } from "@/lib/api";
import type { AudiencePreview, AudienceSource, Page, Role } from "@/lib/types";

import {
  Chip,
  EMAIL,
  ROLE_LABEL,
  parsePaste,
  sourceKey,
  sourceLabel,
  type AcademyChoice,
  type AudienceDraft,
  type AudienceKind,
  type PasteResult,
  type Person,
} from "./AudiencePicker";
import { MenuSelect } from "./MenuSelect";

type Panel = "academy" | "role" | "people" | "outside" | null;
const MAX_SOURCES = 10;

function PersonSearch({ draft, onChange }: { draft: AudienceDraft; onChange: (next: AudienceDraft) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Person[] | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
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
                  disabled={added}
                  onClick={() => onChange({ ...draft, people: [...draft.people, person], excluded: draft.excluded.filter((id) => id !== person.id) })}
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
  );
}

function OutsidePanel({ draft, onChange }: { draft: AudienceDraft; onChange: (next: AudienceDraft) => void }) {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | undefined>();
  const [pasted, setPasted] = useState("");
  const [report, setReport] = useState<PasteResult | null>(null);

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
            {`${report.added.length === 1 ? "Se agregó 1" : `Se agregaron ${report.added.length}`} · ${report.repeated === 1 ? "1 repetido" : `${report.repeated} repetidos`} · ${report.invalid.length === 1 ? "1 inválido" : `${report.invalid.length} inválidos`}`}
          </p>
        )}
        {report && report.invalid.length > 0 && <p className="break-words text-sm text-danger">{`Revisa estos y corrígelos en el cuadro: ${report.invalid.join(", ")}`}</p>}
      </div>
    </div>
  );
}

function AddMenu({ items }: { items: Array<{ label: string; onPick: () => void }> }) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus({ preventScroll: true });
    const away = (event: PointerEvent) => !root.current?.contains(event.target as Node) && setOpen(false);
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  function close(refocus: boolean) {
    setOpen(false);
    if (refocus) trigger.current?.focus();
  }

  function onKey(event: KeyboardEvent<HTMLDivElement>) {
    const nodes = [...(root.current?.querySelectorAll<HTMLButtonElement>("[role=menuitem]") ?? [])];
    const at = nodes.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      nodes[(at + (event.key === "ArrowDown" ? 1 : -1) + nodes.length) % nodes.length]?.focus();
    } else if (event.key === "Tab") {
      close(false);
    }
  }

  return (
    <div ref={root} className="relative">
      <button
        ref={trigger}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
        className={buttonClasses("secondary")}
      >
        <Plus weight="bold" aria-hidden />
        Agregar destinatarios
        <CaretDown size={14} weight="bold" aria-hidden />
      </button>
      {open && (
        <div id={menuId} role="menu" aria-label="Agregar destinatarios" onKeyDown={onKey} className="absolute left-0 z-30 mt-2 grid w-[min(18rem,calc(100vw-3rem))] gap-0.5 rounded-2xl border border-line bg-surface p-2 text-ink shadow-lift">
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              onClick={() => {
                close(false);
                item.onPick();
              }}
              className="min-h-11 rounded-xl px-3 text-left text-sm font-semibold hover:bg-subtle focus-visible:bg-subtle focus-visible:outline-3"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function AudienceSources({
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
  /** A club admin: "Mi club" is added in one click and there is no club select. */
  ownClub?: boolean;
}) {
  const [panel, setPanel] = useState<Panel>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [club, setClub] = useState("");
  const [role, setRole] = useState<Role>("member");
  const [error, setError] = useState<string | null>(null);
  const has = (key: string) => draft.sources.some((s) => sourceKey(s) === key);

  // Each source's own count: the same server resolution as the send, for that source alone.
  useEffect(() => {
    const missing = draft.sources.filter((s) => counts[sourceKey(s)] === undefined);
    if (missing.length === 0) return;
    let live = true;
    for (const source of missing) {
      api<AudiencePreview>("/mail/audience/preview", { method: "POST", json: { kind: "mix", sources: [source], user_ids: [], exclude_user_ids: [], emails: [] } })
        .then((out) => live && setCounts((c) => ({ ...c, [sourceKey(source)]: out.count })))
        .catch(() => undefined); // the chip works without its number
    }
    return () => {
      live = false;
    };
  }, [draft.sources, counts]);

  function addSource(source: AudienceSource) {
    if (has(sourceKey(source))) return;
    if (draft.sources.length >= MAX_SOURCES) return setError(`Máximo ${MAX_SOURCES} fuentes por correo.`);
    setError(null);
    onChange({ ...draft, sources: [...draft.sources, source] });
  }

  const items: Array<{ label: string; onPick: () => void }> = [];
  if (kinds.includes("all")) {
    items.push({
      label: "Todo UpiixSol",
      onPick: () => {
        setPanel(null);
        addSource({ kind: "all" });
      },
    });
  }
  if (kinds.includes("academy")) {
    items.push(
      ownClub
        ? {
            label: "Mi club",
            onPick: () => {
              setPanel(null);
              addSource({ kind: "academy", academy_id: academies[0]?.id ?? 0 });
            },
          }
        : { label: "Un club", onPick: () => setPanel("academy") },
    );
  }
  if (kinds.includes("role")) items.push({ label: "Un rol", onPick: () => setPanel("role") });
  if (kinds.includes("individual")) {
    items.push({ label: "Personas", onPick: () => setPanel("people") }, { label: "Correos de fuera", onPick: () => setPanel("outside") });
  }

  const chips: Array<{ key: string; label: string; remove: string; onRemove: () => void }> = draft.sources.map((source) => {
    const key = sourceKey(source);
    const label = sourceLabel(source, academies, ownClub);
    return {
      key,
      label: `${label}${counts[key] === undefined ? "" : ` · ${counts[key]}`}`,
      remove: `Quitar fuente ${label}`,
      onRemove: () => onChange({ ...draft, sources: draft.sources.filter((s) => sourceKey(s) !== key) }),
    };
  });
  if (draft.people.length > 0) chips.push({ key: "people", label: `Personas · ${draft.people.length}`, remove: "Quitar fuente Personas", onRemove: () => onChange({ ...draft, people: [] }) });
  if (draft.emails.length > 0) chips.push({ key: "outside", label: `Correos de fuera · ${draft.emails.length}`, remove: "Quitar fuente Correos de fuera", onRemove: () => onChange({ ...draft, emails: [] }) });

  return (
    <fieldset className="grid gap-4">
      <legend className="mb-2 text-sm font-semibold">Destinatarios</legend>
      <div className="flex flex-wrap items-center gap-2">
        <AddMenu items={items} />
        {chips.length === 0 && <p className="text-sm text-muted">Aún no agregas a nadie.</p>}
      </div>
      {error && (
        <p role="alert" className="text-sm font-semibold text-danger">
          {error}
        </p>
      )}
      {chips.length > 0 && (
        <ul className="flex flex-wrap gap-2" aria-label="Fuentes de destinatarios">
          {chips.map((chip) => (
            <Chip key={chip.key} label={chip.label} remove={chip.remove} onRemove={chip.onRemove} />
          ))}
        </ul>
      )}
      {panel !== null && (
        <div className="grid gap-4">
          {panel === "academy" && (
            <div className="flex flex-wrap items-end gap-2">
              <div className="min-w-0 flex-1 basis-48">
                <MenuSelect
                  label="Club"
                  value={club}
                  placeholder="Elige un club"
                  options={academies.map((a) => ({ value: String(a.id), label: a.name }))}
                  onChange={setClub}
                />
              </div>
              <Button
                type="button"
                variant="secondary"
                disabled={!club || has(`academy:${club}`)}
                onClick={() => {
                  addSource({ kind: "academy", academy_id: Number(club) });
                  setClub("");
                }}
              >
                Agregar club
              </Button>
            </div>
          )}
          {panel === "role" && (
            <div className="flex flex-wrap items-end gap-2">
              <div className="min-w-0 flex-1 basis-48">
                <MenuSelect
                  label="Rol"
                  value={role}
                  options={(Object.keys(ROLE_LABEL) as Role[]).map((r) => ({ value: r, label: ROLE_LABEL[r] }))}
                  onChange={(v) => setRole(v as Role)}
                />
              </div>
              <Button type="button" variant="secondary" disabled={has(`role:${role}`)} onClick={() => addSource({ kind: "role", role })}>
                Agregar rol
              </Button>
            </div>
          )}
          {panel === "people" && <PersonSearch draft={draft} onChange={onChange} />}
          {panel === "outside" && <OutsidePanel draft={draft} onChange={onChange} />}
          <div>
            <Button type="button" variant="secondary" onClick={() => setPanel(null)}>
              Listo
            </Button>
          </div>
        </div>
      )}
    </fieldset>
  );
}
