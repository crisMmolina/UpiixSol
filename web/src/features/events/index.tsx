// UPS-013: events and calendar (month view + list, academy filter). Completes flow step 6 (global event).
//   /calendario           → campus calendar (all academies + global)
//   /a/:slug/eventos      → the academy's events (+ global ones)
import { CalendarBlank, CaretLeft, CaretRight, LinkSimple, ListBullets, MapPin, Plus, SquaresFour, Trash, X } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams, type RouteObject } from "react-router";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { SelectField, TextArea, TextField, fieldErrors } from "@/components/Field";
import { Markdown } from "@/components/Markdown";
import { Modal } from "@/components/Overlay";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState, Notice } from "@/components/States";
import { api, ApiError, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { AcademyCardOut, EventOut, Page, UserMe } from "@/lib/types";
import { AcademyLayout, CampusLayout, useAcademy } from "@/layouts";

export const order = 45;

const WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const monthTitle = new Intl.DateTimeFormat("es-MX", { month: "long", year: "numeric" });
const dayTime = new Intl.DateTimeFormat("es-MX", { weekday: "long", day: "numeric", month: "long", hour: "numeric", minute: "2-digit" });
const timeOnly = new Intl.DateTimeFormat("es-MX", { hour: "numeric", minute: "2-digit" });

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

/** Monday-first 6×7 grid covering the month. */
function monthGrid(month: Date): Date[] {
  const first = startOfMonth(month);
  const offset = (first.getDay() + 6) % 7;
  return Array.from({ length: 42 }, (_, i) => new Date(first.getFullYear(), first.getMonth(), 1 - offset + i));
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function toLocalInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

const fullDate = new Intl.DateTimeFormat("es-MX", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

function toKey(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Parses `YYYY-MM-DD` as a local date; null when malformed. */
function fromKey(key: string | null): Date | null {
  const m = key ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(key) : null;
  if (!m) return null;
  const date = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return toKey(date) === key ? date : null;
}

function canManage(user: UserMe | null, event?: EventOut): boolean {
  if (!user) return false;
  if (user.role === "superadmin") return true;
  if (user.role !== "academy_admin") return false;
  return event ? event.academy_id !== null && event.academy_id === user.academy_id : true;
}

async function fetchAll(query: Record<string, string | boolean | undefined>): Promise<EventOut[]> {
  const items: EventOut[] = [];
  let cursor: string | null = null;
  do {
    const page: Page<EventOut> = await api<Page<EventOut>>("/events", { query: { ...query, cursor, limit: 50 } });
    items.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor && items.length < 500);
  return items;
}

function EventForm({ user, academies, fixedAcademyId, onSaved, onClose }: {
  user: UserMe;
  academies: AcademyCardOut[];
  fixedAcademyId?: number;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Default: tomorrow 17:00–19:00 (computed once, not on every render).
  const [{ start, end }] = useState(() => {
    const begin = new Date();
    begin.setDate(begin.getDate() + 1);
    begin.setHours(17, 0, 0, 0);
    return { start: begin, end: new Date(begin.getTime() + 2 * 3600_000) };
  });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const academyValue = fixedAcademyId ?? (user.role === "academy_admin" ? user.academy_id : Number(form.get("academy_id")) || null);
    const startsAt = new Date(String(form.get("starts_at")));
    const endsAt = new Date(String(form.get("ends_at")));
    if (endsAt < startsAt) return setErrors({ ends_at: "Debe terminar después de empezar." });
    setBusy(true);
    setError(null);
    setErrors({});
    try {
      await api("/events", {
        method: "POST",
        json: {
          academy_id: academyValue,
          title: String(form.get("title")).trim(),
          description: String(form.get("description")),
          location: String(form.get("location")).trim() || null,
          link: String(form.get("link")).trim() || null,
          starts_at: startsAt.toISOString(),
          ends_at: endsAt.toISOString(),
        },
      });
      onSaved();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setErrors(fieldErrors(err.details));
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      <TextField label="Título" name="title" required maxLength={120} error={errors.title} />
      {user.role === "superadmin" && fixedAcademyId === undefined && (
        <SelectField label="Club" name="academy_id" defaultValue="">
          <option value="">Evento global (todo el club)</option>
          {academies.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </SelectField>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Empieza" name="starts_at" type="datetime-local" required defaultValue={toLocalInput(start)} />
        <TextField label="Termina" name="ends_at" type="datetime-local" required defaultValue={toLocalInput(end)} error={errors.ends_at} />
      </div>
      <TextField label="Lugar" name="location" maxLength={200} placeholder="UPIIZ · Laboratorio de cómputo" />
      <TextField label="Link (opcional)" name="link" type="url" placeholder="https://…" error={errors.link} />
      <TextArea label="Descripción" name="description" rows={3} />
      {error && (
        <p role="alert" className="rounded-xl bg-accent-2/10 px-3 py-2 text-sm font-semibold text-accent-2">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" loading={busy}>
          Publicar evento
        </Button>
      </div>
    </form>
  );
}

function EventRow({ event, manageable, onDelete }: { event: EventOut; manageable: boolean; onDelete: () => void }) {
  return (
    <li className="flex gap-3 rounded-2xl border border-line bg-surface p-4">
      <div className="grid size-14 shrink-0 place-items-center rounded-2xl bg-accent/20 text-center leading-tight text-ink">
        <span className="text-lg font-bold">{new Date(event.starts_at).getDate()}</span>
        <span className="text-[0.7rem] uppercase">{new Intl.DateTimeFormat("es-MX", { month: "short" }).format(new Date(event.starts_at))}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-lg">{event.title}</h3>
          <Badge tone={event.academy_slug ? "primary" : "accent"}>{event.academy_slug ? `#${event.academy_slug}` : "Todo el club"}</Badge>
        </div>
        <p className="text-sm text-muted first-letter:uppercase">
          {dayTime.format(new Date(event.starts_at))} – {timeOnly.format(new Date(event.ends_at))}
        </p>
        {event.location && (
          <p className="inline-flex items-center gap-1 text-sm text-muted">
            <MapPin weight="bold" aria-hidden /> {event.location}
          </p>
        )}
        {event.description && <Markdown source={event.description} className="mt-1 text-sm" />}
        {event.link && (
          <a href={event.link} target="_blank" rel="noopener noreferrer nofollow" className="mt-1 inline-flex items-center gap-1 text-sm font-semibold">
            <LinkSimple weight="bold" aria-hidden /> Más información
          </a>
        )}
      </div>
      {manageable && (
        <button type="button" aria-label={`Eliminar ${event.title}`} onClick={onDelete} className="self-start rounded-full p-2 text-accent-2 hover:bg-line/50">
          <Trash weight="bold" />
        </button>
      )}
    </li>
  );
}

function Calendar({ academySlug, fixedAcademyId }: { academySlug?: string; fixedAcademyId?: number }) {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const selected = fromKey(params.get("dia"));
  const [month, setMonth] = useState(() => startOfMonth(fromKey(params.get("dia")) ?? new Date()));
  const [events, setEvents] = useState<EventOut[] | null>(null);
  const [academies, setAcademies] = useState<AcademyCardOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [today] = useState(() => new Date());
  const view = params.get("vista") === "lista" ? "list" : "month";
  const filter = academySlug ?? params.get("academia") ?? "";

  const dayList = selected && events ? events.filter((e) => sameDay(new Date(e.starts_at), selected)) : [];
  const grid = useMemo(() => monthGrid(month), [month]);
  const load = useCallback(async () => {
    try {
      const range =
        view === "month"
          ? { from: grid[0].toISOString(), to: new Date(grid[41].getTime() + 86_400_000).toISOString() }
          : { from: new Date().toISOString() };
      setEvents(await fetchAll({ ...range, academy: filter || undefined }));
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [grid, view, filter]);

  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    api<Page<AcademyCardOut>>("/academies", { query: { limit: 50 } })
      .then((page) => setAcademies(page.items))
      .catch(() => undefined);
  }, []);

  async function remove(event: EventOut) {
    if (!window.confirm(`¿Eliminar "${event.title}"?`)) return;
    try {
      await api(`/events/${event.id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        {view === "month" && (
          <div className="flex items-center gap-1">
            <button type="button" aria-label="Mes anterior" className="grid size-11 place-items-center rounded-full hover:bg-line/60" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>
              <CaretLeft weight="bold" />
            </button>
            <h2 className="min-w-44 text-center text-xl first-letter:uppercase">{monthTitle.format(month)}</h2>
            <button type="button" aria-label="Mes siguiente" className="grid size-11 place-items-center rounded-full hover:bg-line/60" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>
              <CaretRight weight="bold" />
            </button>
          </div>
        )}
        {view === "list" && <h2 className="text-xl">Próximos eventos</h2>}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {!academySlug && (
            <label className="flex items-center gap-2 text-sm font-semibold">
              <span className="sr-only">Filtrar por club</span>
              <select value={filter} onChange={(e) => setParam("academia", e.target.value)} className="min-h-11 rounded-full border border-line bg-surface px-3">
                <option value="">Todos los clubes</option>
                {academies.map((a) => (
                  <option key={a.id} value={a.slug}>
                    {a.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div role="group" aria-label="Vista" className="flex rounded-full bg-line/50 p-1">
            <button type="button" aria-pressed={view === "month"} onClick={() => setParam("vista", "")} className={`inline-flex min-h-9 items-center gap-1 rounded-full px-3 text-sm font-semibold ${view === "month" ? "bg-surface shadow-soft" : "text-muted"}`}>
              <SquaresFour weight="bold" aria-hidden /> Mes
            </button>
            <button type="button" aria-pressed={view === "list"} onClick={() => setParam("vista", "lista")} className={`inline-flex min-h-9 items-center gap-1 rounded-full px-3 text-sm font-semibold ${view === "list" ? "bg-surface shadow-soft" : "text-muted"}`}>
              <ListBullets weight="bold" aria-hidden /> Lista
            </button>
          </div>
          {canManage(user) && (
            <Button icon={<Plus weight="bold" />} onClick={() => setCreating(true)}>
              Nuevo evento
            </Button>
          )}
        </div>
      </div>

      {error && (events === null ? <ErrorState message={error} onRetry={() => void load()} /> : <Notice tone="alert">{error}</Notice>)}

      {events === null ? (
        <div role="status" aria-label="Cargando eventos" className="grid gap-3">
          <Skeleton className="h-96" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : view === "list" ? (
        events.length === 0 ? (
          <EmptyState title="No hay eventos próximos" />
        ) : (
          <ul className="grid gap-3">
            {events.map((event) => (
              <EventRow key={event.id} event={event} manageable={canManage(user, event)} onDelete={() => void remove(event)} />
            ))}
          </ul>
        )
      ) : (
        <>
          <Card className="overflow-hidden">
            <div className="grid grid-cols-7 border-b border-line bg-bg text-center text-xs font-semibold text-muted">
              {WEEKDAYS.map((d) => (
                <div key={d} className="py-2">
                  {d}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7">
              {grid.map((day) => {
                const dayEvents = events.filter((e) => sameDay(new Date(e.starts_at), day));
                const inMonth = day.getMonth() === month.getMonth();
                const isSelected = selected !== null && sameDay(day, selected);
                const count = dayEvents.length;
                const label = `${fullDate.format(day)}${count ? `, ${count} ${count === 1 ? "evento" : "eventos"}` : ", sin eventos"}`;
                return (
                  <div key={day.toISOString()} className={`relative min-h-20 border-b border-r border-line p-1 sm:min-h-28 sm:p-1.5 ${isSelected ? "bg-primary/10" : inMonth ? "" : "bg-bg/60 text-muted"}`}>
                    <button
                      type="button"
                      aria-pressed={isSelected}
                      aria-label={label}
                      onClick={() => setParam("dia", isSelected ? "" : toKey(day))}
                      className={`absolute inset-0 min-h-11 min-w-11 hover:bg-line/40 focus-visible:z-10 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary ${isSelected ? "ring-2 ring-inset ring-primary" : ""}`}
                    />
                    <span className={`pointer-events-none relative inline-grid size-7 place-items-center rounded-full text-xs font-semibold ${sameDay(day, today) ? "bg-primary text-on-primary" : ""}`}>
                      {day.getDate()}
                    </span>
                    {count > 0 && <span aria-hidden className="pointer-events-none absolute right-1.5 top-2 size-2 rounded-full bg-accent" />}
                    <ul className="pointer-events-none relative mt-0.5 grid gap-0.5">
                      {dayEvents.map((event) => (
                        <li key={event.id} title={`${event.title} · ${timeOnly.format(new Date(event.starts_at))}`} className={`truncate rounded-md px-1 py-0.5 text-[0.7rem] font-semibold ${event.academy_slug ? "bg-primary/15 text-ink" : "bg-accent/25 text-ink"}`}>
                          <span className="hidden sm:inline">{timeOnly.format(new Date(event.starts_at))} </span>
                          {event.title}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </Card>
          {selected ? (
            <section aria-label="Eventos del día seleccionado">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <h3 className="inline-flex items-center gap-1.5 text-lg first-letter:uppercase">
                  <CalendarBlank weight="bold" aria-hidden /> {fullDate.format(selected)}
                </h3>
                <button type="button" onClick={() => setParam("dia", "")} className="inline-flex min-h-11 items-center gap-1 rounded-full border border-line bg-surface px-4 text-sm font-semibold hover:bg-line/50">
                  <X weight="bold" aria-hidden /> Quitar filtro
                </button>
              </div>
              {dayList.length === 0 ? (
                <EmptyState title="Sin eventos este día" />
              ) : (
                <ul className="grid gap-3">
                  {dayList.map((event) => (
                    <EventRow key={event.id} event={event} manageable={canManage(user, event)} onDelete={() => void remove(event)} />
                  ))}
                </ul>
              )}
            </section>
          ) : (
            events.length > 0 && (
              <section aria-label="Eventos del mes">
                <h3 className="mb-2 inline-flex items-center gap-1.5 text-lg">
                  <CalendarBlank weight="bold" aria-hidden /> Este mes
                </h3>
                <ul className="grid gap-3">
                  {events.map((event) => (
                    <EventRow key={event.id} event={event} manageable={canManage(user, event)} onDelete={() => void remove(event)} />
                  ))}
                </ul>
              </section>
            )
          )}
        </>
      )}

      <Modal open={creating} onClose={() => setCreating(false)} title="Nuevo evento">
        {creating && user && (
          <EventForm user={user} academies={academies} fixedAcademyId={fixedAcademyId} onSaved={() => void load()} onClose={() => setCreating(false)} />
        )}
      </Modal>
    </div>
  );
}

function CampusCalendarPage() {
  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-3xl sm:text-4xl">Calendario</h1>
        <p className="text-muted">Talleres, sesiones, hackatones y eventos en todos los clubes</p>
      </div>
      <Calendar />
    </div>
  );
}

function AcademyEventsPage() {
  const academy = useAcademy();
  const { user } = useAuth();
  const [academyId, setAcademyId] = useState<number | undefined>(undefined);
  useEffect(() => {
    api<{ id: number }>(`/academies/${academy.slug}`)
      .then((a) => setAcademyId(a.id))
      .catch(() => undefined);
  }, [academy.slug]);
  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-3xl sm:text-4xl">Eventos de {academy.name}</h1>
        <p className="text-muted">Incluye los eventos para todo el club.</p>
      </div>
      <Calendar academySlug={academy.slug} fixedAcademyId={user?.role === "superadmin" ? academyId : undefined} />
    </div>
  );
}

export const routes: RouteObject[] = [
  {
    element: (
      <RequireRole>
        <CampusLayout />
      </RequireRole>
    ),
    children: [{ path: "/calendario", element: <CampusCalendarPage /> }],
  },
  {
    path: "/a/:slug",
    element: (
      <RequireRole>
        <AcademyLayout />
      </RequireRole>
    ),
    children: [{ path: "eventos", element: <AcademyEventsPage /> }],
  },
];
