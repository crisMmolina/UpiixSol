// Flow step 5 (UPS-008): academy panel — identity, routes → modules → lessons, enrollees.
//   /panel/academia          → the academy of the logged-in academy_admin
//   /panel/academia/:slug    → any academy (superadmin)
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  DotsSixVertical,
  Eye,
  EyeSlash,
  ImageSquare,
  PencilSimple,
  Plus,
  Trash,
  UserMinus,
  UserPlus,
  Warning,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useParams, useSearchParams, type RouteObject } from "react-router";

import { Badge } from "@/components/Badge";
import { Button, ButtonLink } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextArea, TextField, fieldErrors } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { AnimatedHeight } from "@/components/Motion";
import { Modal } from "@/components/Overlay";
import { ProgressBar } from "@/components/ProgressBar";
import { PageSkeleton, Skeleton, SkeletonText } from "@/components/Skeleton";
import { EmptyState, ErrorState, Notice } from "@/components/States";
import { api, ApiError, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import { SITE, Wordmark } from "@/lib/brand";
import { AcademyTheme, contrastRatio, meetsAA, readableTextOn, safeAssetPath } from "@/lib/theme";
import type { AcademyOut, BrandingUpdateIn, LessonLinkOut, Page } from "@/lib/types";
import { ResourceBoard } from "@/features/resources/ResourceBoard";
import { CampusLayout } from "@/layouts";

import { formatClock, parseClock, startFromUrl } from "./clock";
import { ClubMailTab } from "@/features/mail";
import { useSortable } from "./sortable";

export const order = 50;

// ── Contract (feature-local, mirrors app/services/academy_admin.py) ──

interface LessonAdminOut {
  id: number;
  module_id: number;
  title: string;
  youtube_url: string;
  youtube_video_id: string;
  description: string;
  duration_min: number | null;
  start_s: number | null;
  end_s: number | null;
  position: number;
  is_published: boolean;
  links: LessonLinkOut[];
}
interface ModuleAdminOut {
  id: number;
  route_id: number;
  title: string;
  position: number;
  lessons: LessonAdminOut[];
}
interface RouteAdminOut {
  id: number;
  academy_id: number;
  title: string;
  description: string;
  position: number;
  is_published: boolean;
  modules: ModuleAdminOut[];
}
interface ContentOut {
  academy_id: number;
  routes: RouteAdminOut[];
}
interface EnrolleeOut {
  user_id: number;
  full_name: string;
  nickname: string;
  email: string;
  boleta: string | null;
  enrolled_at: string;
}

type Tab = "identidad" | "contenido" | "recursos" | "inscritos" | "correos";

function move<T extends { id: number }>(items: T[], index: number, delta: -1 | 1): number[] {
  const ids = items.map((item) => item.id);
  const target = index + delta;
  [ids[index], ids[target]] = [ids[target], ids[index]];
  return ids;
}

function IconButton({ label, onClick, children, disabled, danger }: {
  label: string;
  onClick: () => void;
  children: ReactNode;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={`grid size-11 place-items-center rounded-full transition hover:bg-line/60 disabled:opacity-30 ${danger ? "text-accent-2" : "text-ink"}`}
    >
      {children}
    </button>
  );
}

// ── Identity ─────────────────────────────────────────────────

const COLOR_FIELDS: { key: "color_primary" | "color_secondary" | "color_accent" | "color_accent_2"; label: string }[] = [
  { key: "color_primary", label: "Primario (botones, barras)" },
  { key: "color_secondary", label: "Secundario (hover, títulos)" },
  { key: "color_accent", label: "Acento" },
  { key: "color_accent_2", label: "Acento 2 (opcional)" },
];

function IdentityTab({ academy, onSaved }: { academy: AcademyOut; onSaved: (a: AcademyOut) => void }) {
  const [draft, setDraft] = useState<AcademyOut>(academy);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  const dirty = (["short_description", "welcome_text", ...COLOR_FIELDS.map((f) => f.key)] as const).some(
    (key) => draft[key] !== academy[key],
  );
  const primaryOk = meetsAA(draft.color_primary);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    const payload: BrandingUpdateIn = {
      short_description: draft.short_description,
      welcome_text: draft.welcome_text,
      color_primary: draft.color_primary,
      color_secondary: draft.color_secondary,
      color_accent: draft.color_accent,
      color_accent_2: draft.color_accent_2 || null,
    };
    try {
      const saved = await api<AcademyOut>(`/academies/${academy.id}/branding`, { method: "PATCH", json: payload });
      onSaved(saved);
      setDraft(saved);
      setMessage({ tone: "ok", text: "Identidad guardada. El tema ya se aplica en todo el club." });
    } catch (err) {
      setMessage({ tone: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  async function upload(kind: "logo" | "mascot", file: File | undefined) {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    setMessage(null);
    try {
      const saved = await api<AcademyOut>(`/academies/${academy.id}/${kind}`, { method: "POST", form });
      onSaved(saved);
      setDraft((d) => ({ ...d, logo_url: saved.logo_url, mascot_url: saved.mascot_url }));
      setMessage({ tone: "ok", text: kind === "logo" ? "Logo actualizado." : "Mascota actualizada." });
    } catch (err) {
      setMessage({ tone: "error", text: errorMessage(err) });
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
      <form onSubmit={save} className="grid gap-5">
        <Card className="grid gap-4 p-5">
          <h3 className="text-lg">Colores</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            {COLOR_FIELDS.map(({ key, label }) => {
              const value = draft[key] ?? "";
              return (
                <div key={key} className="flex items-end gap-2">
                  <input
                    type="color"
                    aria-label={`${label}: selector`}
                    value={value || "#ffffff"}
                    onChange={(e) => setDraft({ ...draft, [key]: e.target.value.toUpperCase() })}
                    className="mb-1 h-11 w-12 shrink-0 cursor-pointer rounded-lg border border-line bg-surface p-1"
                  />
                  <div className="flex-1">
                    <TextField
                      label={label}
                      value={value}
                      placeholder={key === "color_accent_2" ? "Sin color" : "#RRGGBB"}
                      onChange={(e) => setDraft({ ...draft, [key]: e.target.value.toUpperCase() })}
                      pattern="^#[0-9A-Fa-f]{6}$"
                      maxLength={7}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          {!primaryOk && (
            <Notice tone="alert">
              <span className="inline-flex items-center gap-1.5">
                <Warning weight="bold" aria-hidden /> El texto sobre el color primario no alcanza contraste AA (
                {contrastRatio(readableTextOn(draft.color_primary), draft.color_primary).toFixed(2)}:1). Usa un tono más
                claro u oscuro.
              </span>
            </Notice>
          )}
        </Card>

        <Card className="grid gap-4 p-5">
          <h3 className="text-lg">Textos</h3>
          <TextField
            label="Descripción corta"
            value={draft.short_description}
            maxLength={200}
            onChange={(e) => setDraft({ ...draft, short_description: e.target.value })}
            hint="Aparece en la tarjeta del club."
          />
          <TextArea
            label="Texto de bienvenida (markdown)"
            value={draft.welcome_text}
            onChange={(e) => setDraft({ ...draft, welcome_text: e.target.value })}
            rows={5}
          />
        </Card>

        <Card className="grid gap-4 p-5 sm:grid-cols-2">
          {(["logo", "mascot"] as const).map((kind) => {
            const current = safeAssetPath(kind === "logo" ? draft.logo_url : draft.mascot_url);
            return (
              <label key={kind} className="grid cursor-pointer gap-2 rounded-2xl border border-dashed border-line p-4 text-center hover:bg-line/30">
                <span className="text-sm font-semibold">{kind === "logo" ? "Logo" : "Mascota"}</span>
                {current ? (
                  <img src={current} alt="" className="mx-auto h-20 w-auto object-contain" />
                ) : (
                  <ImageSquare size={40} className="mx-auto text-muted" aria-hidden />
                )}
                <span className="text-xs text-muted">PNG, JPG, WebP o SVG · máx. 2 MB</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  className="sr-only"
                  onChange={(e) => void upload(kind, e.target.files?.[0])}
                />
              </label>
            );
          })}
        </Card>

        <FormMessage message={message?.text} tone={message?.tone === "ok" ? "success" : "error"} lines={{ base: 2, sm: 1 }} />
        <div className="-mt-3 flex gap-3">
          <Button type="submit" loading={busy} disabled={!dirty}>
            Guardar identidad
          </Button>
          <Button variant="ghost" disabled={!dirty} onClick={() => setDraft(academy)}>
            Descartar cambios
          </Button>
        </div>
      </form>

      <aside className="lg:sticky lg:top-24 lg:self-start" aria-label="Vista previa">
        <p className="mb-2 text-sm font-semibold text-muted">Vista previa en vivo</p>
        <AcademyTheme branding={draft}>
          <Card stripe className="grid gap-3 p-5">
            {safeAssetPath(draft.logo_url) ? (
              <img src={safeAssetPath(draft.logo_url)!} alt="" className="h-9 w-auto self-start" />
            ) : (
              <Wordmark name={draft.name} colors={draft} className="block truncate text-2xl" />
            )}
            <p className="text-sm text-muted">{draft.short_description || "Descripción corta"}</p>
            <ProgressBar percent={62} label="Ejemplo de progreso" />
            <div className="flex flex-wrap gap-2">
              <Button size="sm">Continuar</Button>
              <Badge tone="accent">Nuevo</Badge>
            </div>
          </Card>
        </AcademyTheme>
      </aside>
    </div>
  );
}

// ── Content ──────────────────────────────────────────────────

const CLOCK_HINT = "mm:ss o h:mm:ss";
const CLOCK_ERROR = "Usa mm:ss o h:mm:ss.";
const SEGMENT_ERROR = "El fin del tramo debe ser mayor que el inicio.";

/** "14:10–48:58" for a lesson that plays only part of its video (UPS-048). */
function segmentLabel(lesson: Pick<LessonAdminOut, "start_s" | "end_s">): string | null {
  if (lesson.start_s == null && lesson.end_s == null) return null;
  return `${formatClock(lesson.start_s ?? 0)}–${lesson.end_s == null ? "fin" : formatClock(lesson.end_s)}`;
}

interface LessonFormState {
  moduleId: number;
  lesson?: LessonAdminOut;
}

function LessonForm({ state, onClose, onSaved }: { state: LessonFormState; onClose: () => void; onSaved: () => void }) {
  const editing = state.lesson;
  const [links, setLinks] = useState(editing?.links.map(({ label, url }) => ({ label, url })) ?? []);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [start, setStart] = useState(editing?.start_s != null ? formatClock(editing.start_s) : "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const duration = String(form.get("duration_min") || "").trim();
    const startText = start.trim();
    const endText = String(form.get("end_s") || "").trim();
    const startS = startText ? parseClock(startText) : null;
    const endS = endText ? parseClock(endText) : null;
    const segmentErrors: Record<string, string> = {};
    if (startText && startS === null) segmentErrors.start_s = CLOCK_ERROR;
    if (endText && endS === null) segmentErrors.end_s = CLOCK_ERROR;
    else if (endS !== null && endS <= (startS ?? 0)) segmentErrors.end_s = SEGMENT_ERROR;
    if (Object.keys(segmentErrors).length) {
      setErrors(segmentErrors);
      setError(segmentErrors.end_s ?? segmentErrors.start_s);
      return;
    }
    const payload = {
      title: String(form.get("title")).trim(),
      youtube_url: String(form.get("youtube_url")).trim(),
      description: String(form.get("description")),
      duration_min: duration ? Number(duration) : null,
      start_s: startS,
      end_s: endS,
      is_published: form.get("is_published") === "on",
      links: links.filter((l) => l.label.trim() && l.url.trim()),
    };
    setBusy(true);
    setError(null);
    setErrors({});
    try {
      if (editing) await api(`/lessons/${editing.id}`, { method: "PATCH", json: payload });
      else await api(`/modules/${state.moduleId}/lessons`, { method: "POST", json: payload });
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
    <form
      onSubmit={submit}
      onChange={(event) => {
        // Editing clears that field's error and the form message (one message at a time, web/DESIGN.md).
        const name = (event.target as Element).getAttribute("name");
        setError(null);
        if (name && name in errors) setErrors(Object.fromEntries(Object.entries(errors).filter(([key]) => key !== name)));
      }}
      className="grid gap-4"
      noValidate
    >
      <TextField label="Título de la clase" name="title" defaultValue={editing?.title} required maxLength={120} reserve error={errors.title} />
      <TextField
        label="URL de YouTube"
        name="youtube_url"
        defaultValue={editing?.youtube_url}
        required
        placeholder="https://www.youtube.com/watch?v=…"
        hint="Acepta watch, youtu.be, shorts o embed."
        error={errors.youtube_url}
        onChange={(event) => {
          // A pasted ?t= fills an empty start; a start the admin typed stays (UPS-048).
          const fromUrl = startFromUrl(event.currentTarget.value);
          if (!start.trim() && fromUrl !== null) setStart(formatClock(fromUrl));
        }}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="Inicio del tramo"
          name="start_s"
          value={start}
          onChange={(event) => setStart(event.currentTarget.value)}
          inputMode="numeric"
          placeholder="0:00"
          hint={CLOCK_HINT}
          reserve
          error={errors.start_s}
        />
        <TextField
          label="Fin del tramo"
          name="end_s"
          defaultValue={editing?.end_s != null ? formatClock(editing.end_s) : ""}
          inputMode="numeric"
          placeholder="Hasta el final"
          hint={CLOCK_HINT}
          reserve
          error={errors.end_s}
        />
      </div>
      <TextArea label="Descripción (markdown)" name="description" defaultValue={editing?.description} rows={4} reserve error={errors.description} />
      <TextField
        label="Duración (minutos)"
        name="duration_min"
        type="number"
        min={1}
        max={600}
        defaultValue={editing?.duration_min ?? ""}
        reserve
        error={errors.duration_min}
      />
      <fieldset className="grid gap-2">
        <legend className="text-sm font-semibold">Recursos de la clase (links)</legend>
        {links.map((link, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[1fr_2fr_auto]">
            <input
              aria-label={`Etiqueta del link ${i + 1}`}
              placeholder="Etiqueta"
              value={link.label}
              onChange={(e) => setLinks(links.map((l, j) => (j === i ? { ...l, label: e.target.value } : l)))}
              className="min-w-0 rounded-xl border border-line px-3 py-2"
            />
            <input
              aria-label={`URL del link ${i + 1}`}
              placeholder="https://…"
              value={link.url}
              onChange={(e) => setLinks(links.map((l, j) => (j === i ? { ...l, url: e.target.value } : l)))}
              className="min-w-0 rounded-xl border border-line px-3 py-2"
            />
            <IconButton label="Quitar link" danger onClick={() => setLinks(links.filter((_, j) => j !== i))}>
              <Trash weight="bold" />
            </IconButton>
          </div>
        ))}
        <Button variant="ghost" size="sm" className="justify-self-start" icon={<Plus weight="bold" />} onClick={() => setLinks([...links, { label: "", url: "" }])}>
          Agregar link
        </Button>
      </fieldset>
      <label className="flex items-center gap-2 text-sm font-semibold">
        <input type="checkbox" name="is_published" defaultChecked={editing?.is_published ?? true} className="size-4" />
        Publicada (visible para los miembros)
      </label>
      <div className="grid gap-2">
        <FormMessage message={error} lines={{ base: 2, sm: 1 }} />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={busy}>
            {editing ? "Guardar clase" : "Agregar clase"}
          </Button>
        </div>
      </div>
    </form>
  );
}

function TitlePrompt({ title, initial, onSubmit, onClose }: {
  title: string;
  initial?: string;
  onSubmit: (value: string) => Promise<void>;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="grid gap-4"
      onSubmit={async (event) => {
        event.preventDefault();
        const value = String(new FormData(event.currentTarget).get("title")).trim();
        if (!value) return setError("Escribe un título.");
        setBusy(true);
        try {
          await onSubmit(value);
          onClose();
        } catch (err) {
          setError(errorMessage(err));
        } finally {
          setBusy(false);
        }
      }}
    >
      <TextField
        label={title}
        name="title"
        defaultValue={initial}
        maxLength={120}
        autoFocus
        reserve
        error={error ?? undefined}
        onChange={() => setError(null)}
      />
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" loading={busy}>
          Guardar
        </Button>
      </div>
    </form>
  );
}

type Dialog =
  | { kind: "lesson"; state: LessonFormState }
  | { kind: "title"; heading: string; title: string; initial?: string; submit: (value: string) => Promise<void> }
  | null;

function dialogTitle(dialog: Exclude<Dialog, null>): string {
  if (dialog.kind === "title") return dialog.heading;
  return dialog.state.lesson ? "Editar clase" : "Nueva clase";
}

/** Same footprint as a route card with one module, so the list does not jump when it loads. */
function ContentSkeleton() {
  return (
    <div role="status" aria-label="Cargando contenido" className="grid gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Skeleton className="h-4 w-full max-w-md" />
        <Skeleton className="h-11 w-36 rounded-full" />
      </div>
      {[0, 1].map((i) => (
        <div key={i} className="grid gap-4 rounded-card border border-line bg-surface p-5">
          <Skeleton className="h-7 w-1/2" />
          <div className="grid gap-2 border-t border-line pt-4">
            <Skeleton className="h-5 w-2/3" />
            <SkeletonText lines={3} />
          </div>
          <Skeleton className="h-9 w-40 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/** Like the enrollees card: the boleta form and a few table rows. */
function EnrolleesSkeleton() {
  return (
    <div role="status" aria-label="Cargando inscritos" className="grid gap-3 rounded-card border border-line bg-surface p-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-4 py-2">
          <div className="grid flex-1 gap-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
          <Skeleton className="hidden h-3.5 w-24 sm:block" />
          <Skeleton className="size-11 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/** A 403/404 cannot be fixed by retrying: show the message without the "Reintentar" button. */
function retryable(err: unknown): boolean {
  return !(err instanceof ApiError && (err.status === 403 || err.status === 404));
}

function ContentTab({ academy }: { academy: AcademyOut }) {
  const [content, setContent] = useState<ContentOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [canRetry, setCanRetry] = useState(true);
  const [dialog, setDialog] = useState<Dialog>(null);
  // The modal keeps showing the last dialog while it animates out: keep its title too.
  const [lastDialog, setLastDialog] = useState<Exclude<Dialog, null> | null>(null);
  if (dialog && dialog !== lastDialog) setLastDialog(dialog);
  const sortable = useSortable();

  const load = useCallback(
    () =>
      api<ContentOut>(`/academies/${academy.id}/content`)
        .then((data) => {
          setContent(data);
          setError(null);
        })
        .catch((err) => {
          setCanRetry(retryable(err));
          setError(errorMessage(err));
        }),
    [academy.id],
  );
  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>) {
    try {
      await action();
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const confirmDelete = (what: string, path: string) => {
    if (window.confirm(`¿Eliminar ${what}? Esta acción no se puede deshacer.`)) void run(() => api(path, { method: "DELETE" }));
  };
  const reorder = (path: string, ids: number[]) => void run(() => api(path, { method: "PUT", json: { ids } }));

  if (!content) return error ? <ErrorState message={error} onRetry={canRetry ? () => void load() : undefined} /> : <ContentSkeleton />;

  return (
    <div className="grid gap-5">
      {error && <Notice tone="alert">{error}</Notice>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">
          Arrastra módulos y clases para ordenarlos, o usa las flechas. Lo que no esté publicado solo lo ves tú.
        </p>
        <Button
          icon={<Plus weight="bold" />}
          onClick={() =>
            setDialog({
              kind: "title",
              heading: "Nueva ruta",
              title: "Título de la nueva ruta",
              submit: (title) => api(`/academies/${academy.id}/routes`, { method: "POST", json: { title } }).then(load),
            })
          }
        >
          Nueva ruta
        </Button>
      </div>

      {content.routes.length === 0 && <EmptyState title="Aún no hay rutas" description="Crea la primera ruta de tu club." mascotUrl={academy.mascot_url} />}

      {content.routes.map((route, routeIndex) => (
        <Card key={route.id} className="grid gap-4 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="mr-auto text-xl">{route.title}</h3>
            <Badge tone={route.is_published ? "primary" : "alert"}>{route.is_published ? "Publicada" : "Borrador"}</Badge>
            {/* One unit, as in the module rows: on a phone the whole toolbar moves under the title, never one icon. */}
            <span className="ml-auto flex shrink-0 items-center">
            <IconButton label="Subir ruta" disabled={routeIndex === 0} onClick={() => reorder(`/academies/${academy.id}/routes/order`, move(content.routes, routeIndex, -1))}>
              <ArrowUp weight="bold" />
            </IconButton>
            <IconButton
              label="Bajar ruta"
              disabled={routeIndex === content.routes.length - 1}
              onClick={() => reorder(`/academies/${academy.id}/routes/order`, move(content.routes, routeIndex, 1))}
            >
              <ArrowDown weight="bold" />
            </IconButton>
            <IconButton
              label={route.is_published ? "Despublicar ruta" : "Publicar ruta"}
              onClick={() => void run(() => api(`/routes/${route.id}`, { method: "PATCH", json: { is_published: !route.is_published } }))}
            >
              {route.is_published ? <EyeSlash weight="bold" /> : <Eye weight="bold" />}
            </IconButton>
            <IconButton
              label="Renombrar ruta"
              onClick={() =>
                setDialog({
                  kind: "title",
                  heading: "Renombrar ruta",
                  title: "Título de la ruta",
                  initial: route.title,
                  submit: (title) => api(`/routes/${route.id}`, { method: "PATCH", json: { title } }).then(load),
                })
              }
            >
              <PencilSimple weight="bold" />
            </IconButton>
            <IconButton label="Eliminar ruta" danger onClick={() => confirmDelete(`la ruta "${route.title}"`, `/routes/${route.id}`)}>
              <Trash weight="bold" />
            </IconButton>
            </span>
          </div>

          {/* Modules are divider sections of the route card, not boxes inside it: one line between them. */}
          <ol className="grid">
            {route.modules.map((module, moduleIndex) => (
              <li
                key={module.id}
                className="cursor-grab rounded-xl border-t border-line pt-4 first:border-t-0 first:pt-0 data-[dragging]:opacity-50 data-[over]:ring-2 data-[over]:ring-secondary"
                {...sortable.item(`route-${route.id}`, route.modules.map((m) => m.id), module.id, (ids) =>
                  reorder(`/routes/${route.id}/modules/order`, ids),
                )}
              >
                {/* Title and controls are two units: on a narrow screen the whole toolbar moves under the
                    title instead of single icons wrapping one by one. */}
                <div className="flex flex-wrap items-center gap-x-1 pb-1">
                  <span className="flex min-w-0 flex-1 basis-48 items-center gap-2 font-semibold">
                    <DotsSixVertical weight="bold" aria-hidden className="shrink-0 text-muted" />
                    Módulo {moduleIndex + 1} · {module.title}
                  </span>
                  <span className="ml-auto flex shrink-0 items-center">
                    <IconButton label="Subir módulo" disabled={moduleIndex === 0} onClick={() => reorder(`/routes/${route.id}/modules/order`, move(route.modules, moduleIndex, -1))}>
                      <ArrowUp weight="bold" />
                    </IconButton>
                    <IconButton
                      label="Bajar módulo"
                      disabled={moduleIndex === route.modules.length - 1}
                      onClick={() => reorder(`/routes/${route.id}/modules/order`, move(route.modules, moduleIndex, 1))}
                    >
                      <ArrowDown weight="bold" />
                    </IconButton>
                    <IconButton
                      label="Renombrar módulo"
                      onClick={() =>
                        setDialog({
                          kind: "title",
                          heading: "Renombrar módulo",
                          title: "Título del módulo",
                          initial: module.title,
                          submit: (title) => api(`/modules/${module.id}`, { method: "PATCH", json: { title } }).then(load),
                        })
                      }
                    >
                      <PencilSimple weight="bold" />
                    </IconButton>
                    <IconButton label="Eliminar módulo" danger onClick={() => confirmDelete(`el módulo "${module.title}" y sus clases`, `/modules/${module.id}`)}>
                      <Trash weight="bold" />
                    </IconButton>
                  </span>
                </div>
                <ol className="grid gap-1 pt-1">
                  {module.lessons.map((lesson, lessonIndex) => (
                    <li
                      key={lesson.id}
                      className="flex flex-wrap items-center gap-x-1 rounded-xl px-2 py-1 hover:bg-line/30 cursor-grab data-[dragging]:opacity-50 data-[over]:ring-2 data-[over]:ring-secondary"
                      {...sortable.item(`module-${module.id}`, module.lessons.map((l) => l.id), lesson.id, (ids) =>
                        reorder(`/modules/${module.id}/lessons/order`, ids),
                      )}
                    >
                      <span className="flex min-w-0 flex-1 basis-48 items-center gap-2 text-sm">
                        <DotsSixVertical weight="bold" aria-hidden className="shrink-0 text-muted" />
                        <span className="min-w-0">
                          {lessonIndex + 1}. {lesson.title}
                          {lesson.duration_min ? <span className="text-muted"> · {lesson.duration_min} min</span> : null}
                          {segmentLabel(lesson) ? <span className="text-muted tabular-nums"> · {segmentLabel(lesson)}</span> : null}
                        </span>
                        {!lesson.is_published && <Badge tone="alert">Borrador</Badge>}
                      </span>
                      <span className="ml-auto flex shrink-0 items-center">
                        <IconButton label="Subir clase" disabled={lessonIndex === 0} onClick={() => reorder(`/modules/${module.id}/lessons/order`, move(module.lessons, lessonIndex, -1))}>
                          <ArrowUp weight="bold" />
                        </IconButton>
                        <IconButton
                          label="Bajar clase"
                          disabled={lessonIndex === module.lessons.length - 1}
                          onClick={() => reorder(`/modules/${module.id}/lessons/order`, move(module.lessons, lessonIndex, 1))}
                        >
                          <ArrowDown weight="bold" />
                        </IconButton>
                        <IconButton label="Editar clase" onClick={() => setDialog({ kind: "lesson", state: { moduleId: module.id, lesson } })}>
                          <PencilSimple weight="bold" />
                        </IconButton>
                        <IconButton label="Eliminar clase" danger onClick={() => confirmDelete(`la clase "${lesson.title}"`, `/lessons/${lesson.id}`)}>
                          <Trash weight="bold" />
                        </IconButton>
                      </span>
                    </li>
                  ))}
                  <li>
                    <Button variant="ghost" size="sm" icon={<Plus weight="bold" />} onClick={() => setDialog({ kind: "lesson", state: { moduleId: module.id } })}>
                      Agregar clase
                    </Button>
                  </li>
                </ol>
              </li>
            ))}
          </ol>
          <Button
            variant="secondary"
            size="sm"
            className="justify-self-start"
            icon={<Plus weight="bold" />}
            onClick={() =>
              setDialog({
                kind: "title",
                heading: "Nuevo módulo",
                title: "Título del nuevo módulo",
                submit: (title) =>
                  api(`/academies/${academy.id}/routes/${route.id}/modules`, { method: "POST", json: { title } }).then(load),
              })
            }
          >
            Agregar módulo
          </Button>
        </Card>
      ))}

      <Modal open={dialog !== null} onClose={() => setDialog(null)} title={lastDialog ? dialogTitle(lastDialog) : ""}>
        {dialog?.kind === "lesson" && <LessonForm state={dialog.state} onClose={() => setDialog(null)} onSaved={() => void load()} />}
        {dialog?.kind === "title" && <TitlePrompt title={dialog.title} initial={dialog.initial} onSubmit={dialog.submit} onClose={() => setDialog(null)} />}
      </Modal>
    </div>
  );
}

// ── Enrollees ────────────────────────────────────────────────

function EnrolleesTab({ academy }: { academy: AcademyOut }) {
  const [items, setItems] = useState<EnrolleeOut[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [canRetry, setCanRetry] = useState(true);
  const [result, setResult] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (after: string | null) => {
      try {
        const page = await api<Page<EnrolleeOut>>(`/academies/${academy.id}/enrollments`, { query: { cursor: after, limit: 50 } });
        setItems((prev) => (after && prev ? [...prev, ...page.items] : page.items));
        setCursor(page.next_cursor);
        setError(null);
      } catch (err) {
        setCanRetry(retryable(err));
        setError(errorMessage(err));
      }
    },
    [academy.id],
  );
  useEffect(() => {
    void load(null);
  }, [load]);

  async function enroll(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const boleta = String(new FormData(formElement).get("boleta")).trim();
    setBusy(true);
    try {
      const added = await api<EnrolleeOut>(`/academies/${academy.id}/enrollments`, { method: "POST", json: { boleta } });
      setResult({ tone: "success", text: `${added.full_name} quedó inscrito.` });
      formElement.reset();
      await load(null);
    } catch (err) {
      setResult({ tone: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  async function remove(person: EnrolleeOut) {
    if (!window.confirm(`¿Dar de baja a ${person.full_name} de ${academy.name}? Su progreso se conserva.`)) return;
    try {
      await api(`/academies/${academy.id}/enrollments/${person.user_id}`, { method: "DELETE" });
      await load(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="grid gap-5">
      <Card className="grid gap-2 p-5">
        <form onSubmit={enroll} className="flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1">
            <TextField
              label="Inscribir por número de boleta"
              name="boleta"
              inputMode="numeric"
              maxLength={10}
              required
              onChange={() => setResult(null)}
            />
          </div>
          <Button type="submit" loading={busy} icon={<UserPlus weight="bold" />}>
            Inscribir
          </Button>
        </form>
        <FormMessage message={result?.text} tone={result?.tone} lines={{ base: 2, sm: 1 }} />
      </Card>
      {error && items && <Notice tone="alert">{error}</Notice>}
      {!items ? (
        error ? (
          <ErrorState message={error} onRetry={canRetry ? () => void load(null) : undefined} />
        ) : (
          <EnrolleesSkeleton />
        )
      ) : items.length === 0 ? (
        <EmptyState title="Aún no hay inscritos" mascotUrl={academy.mascot_url} />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Nombre</th>
                <th className="px-4 py-3 font-semibold">Boleta</th>
                <th className="px-4 py-3 font-semibold">Correo</th>
                <th className="px-4 py-3 font-semibold">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((person) => (
                <tr key={person.user_id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <span className="font-semibold">{person.full_name}</span>
                    <span className="block text-xs text-muted">@{person.nickname}</span>
                  </td>
                  <td className="px-4 py-3 tabular-nums">{person.boleta ?? "—"}</td>
                  <td className="px-4 py-3">{person.email}</td>
                  <td className="px-4 py-3 text-right">
                    <IconButton label={`Dar de baja a ${person.full_name}`} danger onClick={() => void remove(person)}>
                      <UserMinus weight="bold" />
                    </IconButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {cursor && (
            <div className="p-4 text-center">
              <Button variant="secondary" onClick={() => void load(cursor)}>
                Ver más
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────

type PanelLoad =
  | { slug: string; academy: AcademyOut }
  | { slug: string; blocked: "forbidden" | "missing" }
  | { slug: string; error: string };

/** Full-page answer instead of the panel: no club header, tabs or retry (retrying a 403 or a 404 cannot help). */
function PanelBlocked({ kind, slug, ownPanel }: { kind: "forbidden" | "missing"; slug: string; ownPanel: { to: string; label: string } }) {
  const forbidden = kind === "forbidden";
  return (
    <div className="mx-auto grid w-full max-w-xl justify-items-center gap-4 rounded-card border border-line bg-surface px-6 py-12 text-center">
      <img src={SITE.mascotUrl} alt="" className="h-28 w-auto object-contain" />
      <h1 className="text-2xl sm:text-3xl">{forbidden ? "No administras este club" : "Este club no existe"}</h1>
      <p className="max-w-md text-muted">
        {forbidden
          ? "Tu cuenta solo puede editar el panel de tu club. Si necesitas administrar otro, pídelo a la mesa directiva."
          : `No encontramos un club con la dirección “${slug}”. Revisa el enlace o vuelve a tu panel.`}
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        <ButtonLink to={ownPanel.to} icon={<ArrowLeft weight="bold" />}>
          {ownPanel.label}
        </ButtonLink>
        {forbidden && (
          <ButtonLink to={`/a/${slug}`} variant="ghost" icon={<Eye weight="bold" />}>
            Ver el club como miembro
          </ButtonLink>
        )}
      </div>
    </div>
  );
}

function AcademyPanel() {
  const { user } = useAuth();
  const params = useParams<{ slug?: string }>();
  const [search, setSearch] = useSearchParams();
  const slug = params.slug ?? user?.academy_slug ?? null;
  const [load, setLoad] = useState<PanelLoad | null>(null);
  const [attempt, setAttempt] = useState(0);
  const tab: Tab = (["identidad", "contenido", "recursos", "inscritos", "correos"] as const).find((t) => t === search.get("tab")) ?? "contenido";
  // An academy admin can only manage their own club: say so instead of opening a panel whose tabs all 403.
  const ownAcademyId = user?.role === "academy_admin" ? (user.academy_id ?? -1) : null;

  useEffect(() => {
    if (!slug) return;
    let current = true;
    api<AcademyOut>(`/academies/${slug}`)
      .then((academy) => {
        if (!current) return;
        setLoad(ownAcademyId !== null && academy.id !== ownAcademyId ? { slug, blocked: "forbidden" } : { slug, academy });
      })
      .catch((err) => {
        if (!current) return;
        if (err instanceof ApiError && (err.status === 403 || err.status === 404)) {
          setLoad({ slug, blocked: err.status === 403 ? "forbidden" : "missing" });
        } else setLoad({ slug, error: errorMessage(err) });
      });
    return () => {
      current = false;
    };
  }, [slug, ownAcademyId, attempt]);

  if (!slug) {
    return <EmptyState title="Tu cuenta no tiene un club asignado" description="Pide a la mesa directiva que te asigne uno." />;
  }
  const ownPanel =
    user?.role === "superadmin"
      ? { to: "/admin?tab=academias", label: "Ir a los clubes" }
      : { to: "/panel/academia", label: "Ir al panel de mi club" };
  // Never show the previous club's data under a new address: until this slug loads, it is a skeleton.
  if (!load || load.slug !== slug) return <PageSkeleton />;
  if ("blocked" in load) return <PanelBlocked kind={load.blocked} slug={slug} ownPanel={ownPanel} />;
  if ("error" in load) return <ErrorState message={load.error} onRetry={() => setAttempt((n) => n + 1)} />;
  const { academy } = load;
  const setAcademy = (saved: AcademyOut) => setLoad({ slug, academy: saved });

  const tabs: { id: Tab; label: string }[] = [
    { id: "contenido", label: "Contenido" },
    { id: "identidad", label: "Identidad" },
    { id: "recursos", label: "Recursos" },
    { id: "inscritos", label: "Inscritos" },
    { id: "correos", label: "Correos" },
  ];

  return (
    <AcademyTheme branding={academy}>
      <div className="grid gap-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-link">Panel del club</p>
            <h1 className="text-3xl sm:text-4xl">{academy.name}</h1>
          </div>
          <ButtonLink to={`/a/${academy.slug}`} variant="secondary" icon={<Eye weight="bold" />}>
            Ver como miembro
          </ButtonLink>
        </div>
        <div role="tablist" aria-label="Secciones del panel" className="flex w-full max-w-xl gap-1 rounded-full bg-line/50 p-1">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              role="tab"
              type="button"
              aria-selected={tab === id}
              onClick={() => setSearch({ tab: id }, { replace: true })}
              className={`min-h-11 flex-1 rounded-full text-sm font-semibold ${tab === id ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-ink"}`}
            >
              {label}
            </button>
          ))}
        </div>
        {/* The panel grows or shrinks to each tab's height instead of jumping (nothing sits under it). */}
        <AnimatedHeight>
          <section role="tabpanel">
            {tab === "identidad" && <IdentityTab academy={academy} onSaved={setAcademy} />}
            {tab === "contenido" && <ContentTab academy={academy} />}
            {tab === "recursos" && (
              <ResourceBoard slug={academy.slug} academyId={academy.id} canManage mascotUrl={academy.mascot_url} />
            )}
            {tab === "inscritos" && <EnrolleesTab academy={academy} />}
            {tab === "correos" && <ClubMailTab academy={{ id: academy.id, name: academy.name }} />}
          </section>
        </AnimatedHeight>
      </div>
    </AcademyTheme>
  );
}

export const routes: RouteObject[] = [
  {
    element: (
      <RequireRole roles={["academy_admin", "superadmin"]}>
        <CampusLayout />
      </RequireRole>
    ),
    children: [
      { path: "/panel/academia", element: <AcademyPanel /> },
      { path: "/panel/academia/:slug", element: <AcademyPanel /> },
    ],
  },
];
