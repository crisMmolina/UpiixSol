// Event block (spec 004 §Events): pick a campus event or type one. Times are America/Mexico_City.
import { useEffect, useMemo, useState } from "react";

import { TextArea, TextField } from "@/components/Field";
import { api, errorMessage } from "@/lib/api";
import type { EventOut, Page } from "@/lib/types";

import { endBeforeStart, type Draft } from "./blocks";

type EventDraft = Extract<Draft, { kind: "event" }>;

const TIME_ZONE = "America/Mexico_City";
const when = new Intl.DateTimeFormat("es-MX", { timeZone: TIME_ZONE, weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
const MODES = [
  { mode: "campus", label: "Del calendario" },
  { mode: "typed", label: "Escribir evento" },
] as const;

function normalize(text: string) {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

function CampusPicker({ draft, onChange, academy }: { draft: EventDraft; onChange: (next: EventDraft) => void; academy: string | null | undefined }) {
  const [events, setEvents] = useState<EventOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (academy === undefined) return;
    let current = true;
    // A club admin sees the global events and their club's own; a superadmin sees every club's.
    api<Page<EventOut>>("/events", { query: { from: new Date().toISOString(), limit: 50, academy: academy ?? undefined, include_global: true } })
      .then((page) => current && setEvents(page.items))
      .catch((err) => current && setError(errorMessage(err)));
    return () => {
      current = false;
    };
  }, [academy]);

  const shown = useMemo(() => (events ?? []).filter((e) => normalize(`${e.title} ${e.location ?? ""}`).includes(normalize(query.trim()))), [events, query]);

  return (
    <div className="grid gap-3">
      <TextField label="Buscar evento" type="search" value={query} onChange={(e) => setQuery(e.target.value)} />
      {error && (
        <p role="alert" className="text-sm font-semibold text-danger">
          {error}
        </p>
      )}
      {events === null && !error && <p className="text-sm text-muted">Cargando eventos…</p>}
      {events !== null && shown.length === 0 && <p className="text-sm text-muted">{events.length === 0 ? "No hay eventos próximos en el calendario." : "No hay eventos que coincidan."}</p>}
      <ul aria-label="Eventos del campus" className="grid max-h-72 gap-2 overflow-y-auto">
        {shown.map((event) => {
          const picked = draft.eventId === event.id;
          return (
            <li key={event.id}>
              <button
                type="button"
                aria-pressed={picked}
                onClick={() => onChange({ ...draft, eventId: event.id, eventTitle: event.title, coverUrl: event.cover_url })}
                className={`grid min-h-11 w-full gap-0.5 rounded-xl border px-4 py-2 text-left transition focus-visible:outline-3 ${picked ? "border-ink bg-subtle" : "border-line hover:bg-subtle"}`}
              >
                <span className="font-semibold">{event.title}</span>
                <span className="text-sm text-muted">{[when.format(new Date(event.starts_at)), event.location, event.academy_slug ? null : "Todo UpiixSol"].filter(Boolean).join(" · ")}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function EventBlockEditor({ draft, onChange, academy }: { draft: EventDraft; onChange: (next: Draft) => void; academy: string | null | undefined }) {
  const text = (key: "title" | "place" | "link") => (e: { target: { value: string } }) => onChange({ ...draft, [key]: e.target.value.replace(/[\r\n]+/g, " ") });
  return (
    <div className="grid gap-3">
      <div role="radiogroup" aria-label="Origen del evento" className="flex flex-wrap gap-2">
        {MODES.map(({ mode, label }) => (
          <label key={mode} className={`relative inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border px-4 text-sm font-semibold has-[:focus-visible]:outline-3 ${draft.mode === mode ? "border-ink bg-ink text-surface" : "border-line hover:bg-subtle"}`}>
            <input type="radio" name={`origin-${draft.id}`} className="absolute inset-0 size-full cursor-pointer opacity-0" checked={draft.mode === mode} onChange={() => onChange({ ...draft, mode })} />
            {label}
          </label>
        ))}
      </div>
      {draft.mode === "campus" ? (
        <CampusPicker draft={draft} onChange={onChange} academy={academy} />
      ) : (
        <div className="grid gap-3">
          <TextField label="Título del evento" value={draft.title} maxLength={120} onChange={text("title")} />
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField label="Inicio" type="datetime-local" value={draft.start} onChange={(e) => onChange({ ...draft, start: e.target.value })} hint="Hora de la Ciudad de México." />
            <TextField
              label="Fin"
              type="datetime-local"
              value={draft.end}
              min={draft.start || undefined}
              error={endBeforeStart(draft) ? "La hora de fin debe ser posterior a la de inicio." : undefined}
              onChange={(e) => onChange({ ...draft, end: e.target.value })}
            />
          </div>
          <TextField label="Lugar" value={draft.place} maxLength={200} onChange={text("place")} />
          <TextArea label="Descripción del evento" value={draft.description} maxLength={2000} rows={3} onChange={(e) => onChange({ ...draft, description: e.target.value })} />
          <TextField label="Enlace del evento" type="url" inputMode="url" value={draft.link} placeholder="https://" onChange={text("link")} />
        </div>
      )}
    </div>
  );
}
