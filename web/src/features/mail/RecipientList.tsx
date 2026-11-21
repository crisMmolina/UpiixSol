// Step 3 list (spec 006): everyone the email reaches, one row per person, a checkbox to take them out, the ones who
// cannot receive apart with the reason. Rows and counts come from POST /api/mail/audience/list and /preview, the
// same server resolution as the real send.
import { X } from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/Button";
import { TextField } from "@/components/Field";
import { api, errorMessage } from "@/lib/api";
import type { AudienceMember, AudiencePreview, MixAudience, Page } from "@/lib/types";

import { ROLE_LABEL, type AcademyChoice } from "./AudiencePicker";

const REASON: Record<NonNullable<AudienceMember["reason"]>, string> = {
  inactive: "Cuenta inactiva",
  suppressed: "Se dio de baja o rebotó antes",
  blocked_domain: "Dominio bloqueado",
};

function origin(tag: string, academies: readonly AcademyChoice[], ownClub?: boolean): string {
  if (tag === "all") return "Todo UpiixSol";
  if (tag === "picked") return "Agregado";
  if (tag === "outside") return "De fuera";
  if (tag.startsWith("academy:")) {
    const id = Number(tag.slice(8));
    return ownClub ? "Mi club" : `Club ${academies.find((a) => a.id === id)?.name ?? id}`;
  }
  if (tag.startsWith("role:")) return `Rol: ${ROLE_LABEL[tag.slice(5) as keyof typeof ROLE_LABEL] ?? tag.slice(5)}`;
  return tag;
}

function Face({ member }: { member: AudienceMember }) {
  if (member.avatar_url) return <img src={member.avatar_url} alt="" className="size-9 shrink-0 rounded-full object-cover" loading="lazy" />;
  return (
    <span aria-hidden className="grid size-9 shrink-0 place-items-center rounded-full bg-primary/20 text-xs font-semibold text-ink">
      {(member.name || member.email).slice(0, 2).toUpperCase()}
    </span>
  );
}

function Row({
  member,
  academies,
  ownClub,
  onToggle,
  onRemoveEmail,
}: {
  member: AudienceMember;
  academies: readonly AcademyChoice[];
  ownClub?: boolean;
  onToggle: (userId: number, receives: boolean) => void;
  onRemoveEmail: (email: string) => void;
}) {
  const cannot = member.state === "cannot";
  const outside = member.user_id === null;
  const name = member.name || member.email;
  return (
    <li className={`flex items-center gap-x-3 py-2 ${member.state === "removed" ? "opacity-70" : ""}`}>
      {!cannot && !outside ? (
        <label className="grid size-11 shrink-0 cursor-pointer place-items-center">
          <input
            type="checkbox"
            aria-label={name}
            checked={member.state === "receives"}
            onChange={(e) => onToggle(member.user_id as number, e.target.checked)}
            className="size-5 accent-[var(--color-link)]"
          />
        </label>
      ) : (
        <span aria-hidden className="size-11 shrink-0 max-sm:hidden" />
      )}
      <Face member={member} />
      <div className="grid min-w-0 flex-1">
        <span className="truncate text-sm font-semibold">
          {outside ? member.email : name}
          {member.nickname && <span className="ml-1 font-normal text-muted max-sm:hidden">@{member.nickname}</span>}
        </span>
        {!outside && <span className="truncate text-xs text-muted">{member.email}</span>}
        <span className="truncate text-xs text-muted">{member.origins.map((tag) => origin(tag, academies, ownClub)).join(" · ")}</span>
        {cannot && member.reason && <span className="text-xs font-semibold text-danger">{REASON[member.reason]}</span>}
      </div>
      {outside && (
        <button type="button" aria-label={`Quitar ${member.email}`} onClick={() => onRemoveEmail(member.email)} className="grid size-11 place-items-center rounded-full hover:bg-subtle">
          <X size={16} weight="bold" aria-hidden />
        </button>
      )}
    </li>
  );
}

export function RecipientList({
  audience,
  academies,
  ownClub,
  onToggle,
  onRemoveEmail,
}: {
  audience: MixAudience | null;
  academies: AcademyChoice[];
  ownClub?: boolean;
  onToggle: (userId: number, receives: boolean) => void;
  onRemoveEmail: (email: string) => void;
}) {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<AudienceMember[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [summary, setSummary] = useState<AudiencePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(audience);
  latest.current = audience;

  // The list restarts when the sources, people, addresses or search change; unchecking only flips a row in place
  // (no new page one, no lost scroll).
  const listKey = useMemo(() => (audience ? JSON.stringify([audience.sources, audience.user_ids, audience.emails, q.trim()]) : ""), [audience, q]);
  const summaryKey = useMemo(() => (audience ? JSON.stringify([audience.sources, audience.user_ids, audience.emails, audience.exclude_user_ids]) : ""), [audience]);

  useEffect(() => {
    if (!latest.current) {
      setItems([]);
      setCursor(null);
      return;
    }
    let live = true;
    setLoading(true);
    const timer = window.setTimeout(() => {
      api<Page<AudienceMember>>("/mail/audience/list", { method: "POST", json: { audience: latest.current, q: q.trim() || undefined, limit: 50 } })
        .then((page) => {
          if (!live) return;
          setItems(page.items);
          setCursor(page.next_cursor);
          setError(null);
        })
        .catch((err) => live && setError(errorMessage(err)))
        .finally(() => live && setLoading(false));
    }, 250);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `listKey` stands for the audience and the search
  }, [listKey]);

  useEffect(() => {
    if (!latest.current) return setSummary(null);
    let live = true;
    const timer = window.setTimeout(() => {
      api<AudiencePreview>("/mail/audience/preview", { method: "POST", json: latest.current })
        .then((out) => live && setSummary(out))
        .catch(() => live && setSummary(null));
    }, 150);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, [summaryKey]);

  async function more() {
    if (!latest.current || !cursor) return;
    setLoading(true);
    try {
      const page = await api<Page<AudienceMember>>("/mail/audience/list", { method: "POST", json: { audience: latest.current, q: q.trim() || undefined, cursor, limit: 50 } });
      setItems((current) => [...current, ...page.items]);
      setCursor(page.next_cursor);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function toggle(userId: number, receives: boolean) {
    setItems((current) => current.map((m) => (m.user_id === userId ? { ...m, state: receives ? "receives" : "removed" } : m)));
    onToggle(userId, receives);
  }

  if (!audience) {
    return <p className="rounded-2xl bg-subtle p-4 text-sm text-muted">Agrega una fuente para ver quién recibirá el correo.</p>;
  }

  const cannotList = items.filter((m) => m.state === "cannot");
  const main = items.filter((m) => m.state !== "cannot");
  const cannot = summary ? summary.excluded.inactive + summary.excluded.suppressed + summary.excluded.blocked_domain : 0;
  const removed = summary?.removed ?? 0;

  return (
    <section aria-label="Lista de destinatarios" className="grid gap-3">
      {summary && (
        <p role="status" className="text-sm font-semibold">
          {`${summary.count} recibirán · ${removed} ${removed === 1 ? "quitado" : "quitados"} por ti · ${cannot} no se ${cannot === 1 ? "puede" : "pueden"} enviar`}
        </p>
      )}
      <TextField label="Buscar en la lista" type="search" value={q} autoComplete="off" onChange={(e) => setQ(e.target.value)} hint="Por nombre, apodo o correo." />
      {error && (
        <p role="alert" className="text-sm font-semibold text-danger">
          {error}
        </p>
      )}
      {main.length > 0 && (
        <ul aria-label="Destinatarios" className="divide-y divide-line rounded-2xl border border-line bg-surface px-2">
          {main.map((m) => (
            <Row key={m.user_id ?? m.email} member={m} academies={academies} ownClub={ownClub} onToggle={toggle} onRemoveEmail={onRemoveEmail} />
          ))}
        </ul>
      )}
      {!loading && items.length === 0 && !error && <p className="text-sm text-muted">{q.trim() ? "Nadie coincide con tu búsqueda." : "Esta selección no tiene personas."}</p>}
      {cursor && (
        <div>
          <Button type="button" variant="secondary" loading={loading} onClick={() => void more()}>
            Cargar más
          </Button>
        </div>
      )}
      {cannotList.length > 0 && (
        <div className="grid gap-2">
          <h4 className="text-sm font-semibold">No se pueden enviar</h4>
          <ul aria-label="No se pueden enviar" className="divide-y divide-line rounded-2xl border border-line bg-subtle/50 px-2">
            {cannotList.map((m) => (
              <Row key={m.user_id ?? m.email} member={m} academies={academies} ownClub={ownClub} onToggle={toggle} onRemoveEmail={onRemoveEmail} />
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
