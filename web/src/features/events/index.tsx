// UPS-013: events and calendar (month view + list, academy filter). Completes flow step 6 (global event).
//   /calendario           → campus calendar (all academies + global)
//   /a/:slug/eventos      → the academy's events (+ global ones)
import { CalendarBlank, CaretLeft, CaretRight, LinkSimple, ListBullets, MapPin, Plus, SquaresFour, Trash, X } from "@phosphor-icons/react";
import { useReducedMotion } from "motion/react";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useSearchParams, type RouteObject } from "react-router";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { SelectField, TextArea, TextField, fieldErrors } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Markdown } from "@/components/Markdown";
import { AnimatedHeight } from "@/components/Motion";
import { Modal } from "@/components/Overlay";
import { ListSkeleton, Skeleton } from "@/components/Skeleton";
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

/** A link the API accepts (http or https with a host); empty is fine (the link is optional). */
function validLink(value: string): boolean {
  if (!value) return true;
  try {
    const url = new URL(value);
    return (url.protocol === "https:" || url.protocol === "http:") && url.hostname.includes(".");
  } catch {
    return false;
  }
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
    const title = String(form.get("title")).trim();
    const link = String(form.get("link")).trim();
    const startsAt = new Date(String(form.get("starts_at")));
    const endsAt = new Date(String(form.get("ends_at")));
    const local: Record<string, string> = {};
    if (!title) local.title = "Este campo es obligatorio.";
    if (Number.isNaN(startsAt.getTime())) local.starts_at = "Escribe una fecha válida.";
    if (Number.isNaN(endsAt.getTime())) local.ends_at = "Escribe una fecha válida.";
    else if (endsAt < startsAt) local.ends_at = "Debe terminar después de empezar.";
    if (!validLink(link)) local.link = "Escribe un enlace que empiece con https://.";
    setErrors(local);
    if (Object.keys(local).length > 0) return setError("Revisa los campos marcados.");
    setBusy(true);
    setError(null);
    try {
      await api("/events", {
        method: "POST",
        json: {
          academy_id: academyValue,
          title,
          description: String(form.get("description")),
          location: String(form.get("location")).trim() || null,
          link: link || null,
          starts_at: startsAt.toISOString(),
          ends_at: endsAt.toISOString(),
        },
      });
      onSaved();
      onClose();
    } catch (err) {
      const fields = err instanceof ApiError && err.status === 422 ? fieldErrors(err.details) : {};
      setErrors(fields);
      setError(Object.keys(fields).length > 0 ? "Revisa los campos marcados." : errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  // Typing in a field clears its own error (the form-level message stays until the next submit).
  function clearFieldError(event: FormEvent<HTMLFormElement>) {
    const name = (event.target as HTMLInputElement).name;
    if (!name || !errors[name]) return;
    setErrors((previous) => {
      const next = { ...previous };
      delete next[name];
      return next;
    });
  }

  return (
    <form onSubmit={submit} onChange={clearFieldError} className="grid gap-4" noValidate>
      <TextField label="Título" name="title" required maxLength={120} reserve error={errors.title} />
      {user.role === "superadmin" && fixedAcademyId === undefined && (
        <SelectField label="Club" name="academy_id" defaultValue="" error={errors.academy_id}>
          <option value="">Evento global (todo el club)</option>
          {academies.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </SelectField>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Empieza" name="starts_at" type="datetime-local" required defaultValue={toLocalInput(start)} reserve error={errors.starts_at} />
        <TextField label="Termina" name="ends_at" type="datetime-local" required defaultValue={toLocalInput(end)} reserve error={errors.ends_at} />
      </div>
      <TextField label="Lugar" name="location" maxLength={200} placeholder="UPIIZ · Laboratorio de cómputo" error={errors.location} />
      <TextField label="Link (opcional)" name="link" type="url" inputMode="url" placeholder="https://…" reserve error={errors.link} />
      <TextArea label="Descripción" name="description" rows={3} error={errors.description} />
      <div className="grid gap-2">
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={busy}>
            Publicar evento
          </Button>
        </div>
        <FormMessage message={error} lines={{ base: 2, sm: 1 }} />
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

/** Event rows that fit in a fixed-height month cell (desktop); more show as "+N más". */
const MAX_IN_CELL = 3;

function sameMonth(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
}

function Calendar({ academySlug, fixedAcademyId }: { academySlug?: string; fixedAcademyId?: number }) {
  const { user } = useAuth();
  const reduce = useReducedMotion();
  const [params, setParams] = useSearchParams();
  const dia = params.get("dia");
  const selected = useMemo(() => fromKey(dia), [dia]);
  const [month, setMonth] = useState(() => startOfMonth(fromKey(dia) ?? new Date()));
  // `?dia=` drives the visible month: a shared link, the back button or a day of the next month shown
  // in the grid all move the grid to that day's month (adjusted while rendering, not in an effect).
  const [syncedDia, setSyncedDia] = useState(dia);
  if (dia !== syncedDia) {
    setSyncedDia(dia);
    if (selected && !sameMonth(selected, month)) setMonth(startOfMonth(selected));
  }
  const [data, setData] = useState<{ key: string; items: EventOut[] } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [academies, setAcademies] = useState<AcademyCardOut[]>([]);
  const [creating, setCreating] = useState(false);
  const [formKey, setFormKey] = useState(0);
  const [today] = useState(() => new Date());
  const detailRef = useRef<HTMLElement>(null);
  const scrollToDetail = useRef(false);
  const view = params.get("vista") === "lista" ? "list" : "month";
  const filter = academySlug ?? params.get("academia") ?? "";

  const grid = useMemo(() => monthGrid(month), [month]);
  // One key per request: events of another month, view or club are never shown under this heading.
  const requestKey = `${view}|${view === "month" ? toKey(month) : ""}|${filter}`;

  useEffect(() => {
    let alive = true;
    const range =
      view === "month"
        ? { from: grid[0].toISOString(), to: new Date(grid[41].getTime() + 86_400_000).toISOString() }
        : { from: new Date().toISOString() };
    fetchAll({ ...range, academy: filter || undefined })
      .then((items) => {
        if (!alive) return; // a newer request (month, view or club changed) owns the screen
        setData({ key: requestKey, items });
        setFailure(null);
      })
      .catch((err) => alive && setFailure({ key: requestKey, message: errorMessage(err) }));
    return () => {
      alive = false;
    };
  }, [grid, view, filter, requestKey, version]);

  useEffect(() => {
    api<Page<AcademyCardOut>>("/academies", { query: { limit: 50 } })
      .then((page) => setAcademies(page.items))
      .catch(() => undefined);
  }, []);

  const events = data?.key === requestKey ? data.items : null;
  const error = failure?.key === requestKey ? failure.message : null;
  const reload = () => setVersion((v) => v + 1);

  const byDay = useMemo(() => {
    const map = new Map<string, EventOut[]>();
    for (const event of events ?? []) {
      const key = toKey(new Date(event.starts_at));
      const list = map.get(key);
      if (list) list.push(event);
      else map.set(key, [event]);
    }
    return map;
  }, [events]);
  const dayList = selected ? (byDay.get(toKey(selected)) ?? []) : [];
  const monthEvents = (events ?? []).filter((e) => sameMonth(new Date(e.starts_at), month));

  // A click on a day brings its detail into view when it sits below the fold (desktop: under the grid).
  useEffect(() => {
    if (!scrollToDetail.current || !selected) return;
    scrollToDetail.current = false;
    const section = detailRef.current;
    if (section && section.getBoundingClientRect().top > window.innerHeight - 160) {
      section.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    }
  }, [selected, reduce]);

  async function remove(event: EventOut) {
    if (!window.confirm(`¿Eliminar "${event.title}"?`)) return;
    try {
      await api(`/events/${event.id}`, { method: "DELETE" });
      setActionError(null);
      reload();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  function goMonth(delta: number) {
    setMonth(new Date(month.getFullYear(), month.getMonth() + delta, 1));
    if (dia) setParam("dia", ""); // the selected day left the grid: show the new month's list
  }

  function pickDay(day: Date, isSelected: boolean) {
    scrollToDetail.current = !isSelected;
    setParam("dia", isSelected ? "" : toKey(day));
  }

  const row = (event: EventOut) => (
    <EventRow key={event.id} event={event} manageable={canManage(user, event)} onDelete={() => void remove(event)} />
  );

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        {view === "month" ? (
          <div className="flex items-center gap-1">
            <button type="button" aria-label="Mes anterior" className="grid size-11 place-items-center rounded-full hover:bg-line/60" onClick={() => goMonth(-1)}>
              <CaretLeft weight="bold" />
            </button>
            {/* Fixed width: "septiembre de 2026" and "mayo de 2026" keep the toolbar in place. */}
            <h2 className="w-52 text-center text-xl first-letter:uppercase">{monthTitle.format(month)}</h2>
            <button type="button" aria-label="Mes siguiente" className="grid size-11 place-items-center rounded-full hover:bg-line/60" onClick={() => goMonth(1)}>
              <CaretRight weight="bold" />
            </button>
          </div>
        ) : (
          <h2 className="flex min-h-11 items-center text-xl">Próximos eventos</h2>
        )}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {!academySlug && (
            <label className="flex items-center gap-2 text-sm font-semibold">
              <span className="sr-only">Filtrar por club</span>
              <select value={filter} onChange={(e) => setParam("academia", e.target.value)} className="min-h-11 w-48 rounded-full border border-line bg-surface px-3">
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
            <Button
              icon={<Plus weight="bold" />}
              onClick={() => {
                setFormKey((k) => k + 1); // a fresh form each time it opens
                setCreating(true);
              }}
            >
              Nuevo evento
            </Button>
          )}
        </div>
      </div>

      <p role="status" className="sr-only">
        {events === null && !error ? "Cargando eventos" : ""}
      </p>
      {actionError && <Notice tone="alert">{actionError}</Notice>}

      {error && events === null ? (
        <ErrorState
          message={error}
          onRetry={() => {
            setFailure(null);
            reload();
          }}
        />
      ) : view === "list" ? (
        events === null ? (
          <ListSkeleton rows={4} />
        ) : events.length === 0 ? (
          <EmptyState title="No hay eventos próximos" />
        ) : (
          <ul key={requestKey} className="enter grid gap-3">
            {events.map(row)}
          </ul>
        )
      ) : (
        <>
          <Card className="overflow-hidden" aria-busy={events === null}>
            <div className="grid grid-cols-7 border-b border-line bg-bg text-center text-xs font-semibold text-muted">
              {WEEKDAYS.map((d) => (
                <div key={d} className="py-2">
                  {d}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7">
              {grid.map((day) => {
                const dayEvents = byDay.get(toKey(day)) ?? [];
                const inMonth = day.getMonth() === month.getMonth();
                const isSelected = selected !== null && sameDay(day, selected);
                const count = dayEvents.length;
                const shown = count > MAX_IN_CELL ? dayEvents.slice(0, MAX_IN_CELL - 1) : dayEvents;
                const summary = events === null ? "" : count ? `, ${count} ${count === 1 ? "evento" : "eventos"}` : ", sin eventos";
                return (
                  // Fixed height: a busy month never makes the grid (and what is under it) grow.
                  <div key={toKey(day)} className={`relative h-16 overflow-hidden border-b border-r border-line p-1 sm:h-28 sm:p-1.5 ${isSelected ? "bg-primary/10" : inMonth ? "" : "bg-bg/60 text-muted"}`}>
                    <button
                      type="button"
                      aria-pressed={isSelected}
                      aria-label={`${fullDate.format(day)}${summary}`}
                      onClick={() => pickDay(day, isSelected)}
                      className={`absolute inset-0 min-h-11 min-w-11 hover:bg-line/40 focus-visible:z-10 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary ${isSelected ? "ring-2 ring-inset ring-primary" : ""}`}
                    />
                    <span className={`pointer-events-none relative mx-auto grid size-7 place-items-center rounded-full text-xs font-semibold sm:mx-0 ${sameDay(day, today) ? "bg-primary text-on-primary" : ""}`}>
                      {day.getDate()}
                    </span>
                    {events === null ? (
                      inMonth && <Skeleton className="pointer-events-none relative mx-auto mt-1 h-2.5 w-5 rounded-full sm:mx-0 sm:h-4 sm:w-3/4" />
                    ) : (
                      count > 0 && (
                        <div key={requestKey} aria-hidden className="enter pointer-events-none relative">
                          {/* Phones: a dot and the count; the titles are in the list under the grid. */}
                          <span className="mt-0.5 flex items-center justify-center gap-1 text-xs font-semibold sm:hidden">
                            <span className="size-2 rounded-full bg-accent" />
                            {count}
                          </span>
                          <ul className="mt-0.5 hidden gap-0.5 sm:grid">
                            {shown.map((event) => (
                              <li key={event.id} title={`${event.title} · ${timeOnly.format(new Date(event.starts_at))}`} className={`truncate rounded-md px-1 py-0.5 text-[0.7rem] font-semibold ${event.academy_slug ? "bg-primary/15 text-ink" : "bg-accent/25 text-ink"}`}>
                                {timeOnly.format(new Date(event.starts_at))} {event.title}
                              </li>
                            ))}
                            {count > shown.length && <li className="px-1 text-[0.7rem] font-semibold text-muted">+{count - shown.length} más</li>}
                          </ul>
                        </div>
                      )
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
          <AnimatedHeight>
            {selected ? (
              <section ref={detailRef} aria-label="Eventos del día seleccionado" className="scroll-mt-20">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <h3 className="inline-flex items-center gap-1.5 text-lg first-letter:uppercase">
                    <CalendarBlank weight="bold" aria-hidden /> {fullDate.format(selected)}
                  </h3>
                  <button type="button" onClick={() => setParam("dia", "")} className="inline-flex min-h-11 items-center gap-1 rounded-full border border-line bg-surface px-4 text-sm font-semibold hover:bg-line/50">
                    <X weight="bold" aria-hidden /> Quitar filtro
                  </button>
                </div>
                {events === null ? (
                  <ListSkeleton rows={1} />
                ) : dayList.length === 0 ? (
                  <EmptyState title="Sin eventos este día" />
                ) : (
                  <ul key={`${requestKey}|${dia}`} className="enter grid gap-3">
                    {dayList.map(row)}
                  </ul>
                )}
              </section>
            ) : (
              <section aria-label="Eventos del mes">
                <h3 className="mb-2 inline-flex items-center gap-1.5 text-lg">
                  <CalendarBlank weight="bold" aria-hidden /> Este mes
                </h3>
                {events === null ? (
                  <ListSkeleton rows={3} />
                ) : monthEvents.length === 0 ? (
                  <p className="text-muted">No hay eventos este mes.</p>
                ) : (
                  <ul key={requestKey} className="enter grid gap-3">
                    {monthEvents.map(row)}
                  </ul>
                )}
              </section>
            )}
          </AnimatedHeight>
        </>
      )}

      <Modal open={creating} onClose={() => setCreating(false)} title="Nuevo evento">
        {user && <EventForm key={formKey} user={user} academies={academies} fixedAcademyId={fixedAcademyId} onSaved={reload} onClose={() => setCreating(false)} />}
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
