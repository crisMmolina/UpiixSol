// Course player (UPS-024): immersive dark view, like the reference course player.
//   /a/:slug/clases/:lessonId
// A lesson is marked complete only when its video ends (see youtube.ts); there is no manual button.
import {
  ArrowLeft,
  ArrowRight,
  CaretDown,
  CheckCircle,
  Circle,
  LinkSimple,
  ListBullets,
  MagnifyingGlass,
  PlayCircle,
  WifiSlash,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { Link, useParams } from "react-router";

import { Badge } from "@/components/Badge";
import { ButtonLink } from "@/components/Button";
import { Markdown } from "@/components/Markdown";
import { Drawer } from "@/components/Overlay";
import { Skeleton, SkeletonText } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, ApiError, errorMessage } from "@/lib/api";
import { Toasts } from "@/layouts/Notifications";
import { useNotifications } from "@/lib/notifications";
import { AcademyTheme, safeAssetPath, useAcademyBranding } from "@/lib/theme";
import type { AcademyBranding, LessonOut, RouteDetailOut, RouteProgressOut } from "@/lib/types";

import { playerSrc, useVideoEnded } from "./youtube";

interface CompletionOut {
  lesson_id: number;
  completed: boolean;
  progress: RouteProgressOut;
}

const VIDEO_TIMEOUT_MS = 8000;

// ── Layout: dark course chrome (its own top bar, no app rail) ─

export function CoursePage() {
  const { slug } = useParams<{ slug: string }>();
  const { status, branding, error, retry } = useAcademyBranding(slug);

  return (
    <div data-theme="dark" className="min-h-dvh bg-bg text-ink">
      {status === "ready" ? (
        <AcademyTheme branding={branding}>
          <Player academy={branding} />
        </AcademyTheme>
      ) : status === "error" ? (
        <div className="mx-auto max-w-xl p-6">
          {error instanceof ApiError && error.status === 404 ? (
            <EmptyState title="Este club no existe o ya no está activo" action={<ButtonLink to="/academias">Ver clubes</ButtonLink>} />
          ) : (
            <ErrorState message={errorMessage(error)} onRetry={retry} />
          )}
        </div>
      ) : (
        <PlayerSkeleton />
      )}
      <Toasts />
    </div>
  );
}

function TopBar({ academy, title }: { academy: AcademyBranding; title?: string }) {
  const logo = safeAssetPath(academy.logo_url);
  return (
    <header className="sticky top-0 z-20 grid h-14 grid-cols-[1fr_auto_1fr] items-center gap-3 border-b border-line bg-surface/95 px-3 backdrop-blur sm:px-5">
      <Link to={`/a/${academy.slug}`} className="inline-flex min-h-11 items-center gap-1.5 justify-self-start rounded-full px-2 text-sm font-semibold text-ink no-underline hover:bg-subtle">
        <ArrowLeft size={16} weight="bold" aria-hidden /> Ir a inicio
      </Link>
      {logo ? <img src={logo} alt={academy.name} className="h-6 w-auto sm:h-7" /> : <span className="font-display font-semibold">{academy.name}</span>}
      <span className="hidden min-w-0 justify-self-end truncate text-sm text-muted md:block">{title}</span>
    </header>
  );
}

function PlayerSkeleton() {
  return (
    <div role="status" aria-label="Cargando clase">
      <div className="h-14 border-b border-line bg-surface" />
      <div className="grid lg:grid-cols-[22rem_1fr]">
        <div className="hidden gap-4 border-r border-line bg-surface p-5 lg:grid lg:content-start">
          <Skeleton className="h-7 w-3/4" />
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-10 w-full" />
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
        <div className="grid content-start gap-5 p-4 sm:p-8">
          <Skeleton className="h-7 w-1/2" />
          <Skeleton className="aspect-video w-full rounded-2xl" />
          <SkeletonText lines={3} />
        </div>
      </div>
    </div>
  );
}

// ── Video ────────────────────────────────────────────────────

function VideoFrame({ lesson, onEnded }: { lesson: LessonOut; onEnded: () => void }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable">(() =>
    typeof navigator !== "undefined" && !navigator.onLine ? "unavailable" : "loading",
  );
  useVideoEnded(frame, onEnded, status !== "unavailable");

  useEffect(() => {
    // An <iframe> has no reliable onerror: if it does not load in time (or we are offline) show the fallback.
    const timer = window.setTimeout(() => setStatus((s) => (s === "loading" ? "unavailable" : s)), VIDEO_TIMEOUT_MS);
    const offline = () => setStatus("unavailable");
    window.addEventListener("offline", offline);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("offline", offline);
    };
  }, []);

  return (
    <div
      className="relative aspect-video w-full overflow-hidden rounded-2xl bg-video bg-cover bg-center ring-1 ring-line"
      style={{ backgroundImage: `url("${lesson.thumbnail_url}")` }}
    >
      {status !== "unavailable" && (
        <iframe
          ref={frame}
          className="absolute inset-0 size-full"
          src={playerSrc(lesson.embed_url)}
          title={lesson.title}
          referrerPolicy="strict-origin-when-cross-origin"
          allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
          allowFullScreen
          onLoad={() => setStatus("ready")}
        />
      )}
      {status === "unavailable" && (
        <div role="status" className="absolute inset-0 grid place-items-center bg-video/80 p-6 text-center text-white">
          <div className="grid justify-items-center gap-2">
            <WifiSlash size={40} weight="bold" aria-hidden />
            <p className="text-lg font-semibold">Video no disponible sin conexión</p>
            <p className="text-sm text-white/80">Revisa tu internet o ábrelo directamente en YouTube.</p>
            <a
              href={`https://www.youtube.com/watch?v=${lesson.youtube_video_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 font-semibold text-white underline"
            >
              Abrir en YouTube
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sidebar ──────────────────────────────────────────────────

function CourseSidebar({
  route,
  currentId,
  slug,
  onNavigate,
}: {
  route: RouteDetailOut;
  currentId: number;
  slug: string;
  onNavigate?: () => void;
}) {
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();
  const modules = useMemo(
    () =>
      route.modules.map((module) => ({
        ...module,
        lessons: needle ? module.lessons.filter((l) => l.title.toLowerCase().includes(needle)) : module.lessons,
      })),
    [route.modules, needle],
  );
  const percent = route.progress?.percent ?? 0;

  return (
    <nav aria-label="Contenido de la ruta" className="grid gap-5">
      <div className="rounded-card bg-subtle p-4 ring-1 ring-line">
        <h2 className="text-2xl leading-tight">{route.title}</h2>
        <div
          className="mt-4 h-1.5 overflow-hidden rounded-full bg-line"
          role="progressbar"
          aria-label="Progreso de la ruta"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${percent}%` }} />
        </div>
        <p className="mt-2 text-sm font-semibold tabular-nums">{percent} % completado</p>
      </div>
      <label className="relative block">
        <span className="sr-only">Buscar por el título de la lección</span>
        <MagnifyingGlass size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar por el título de la lección"
          className="w-full rounded-[var(--radius-field)] border border-line bg-subtle py-2.5 pl-10 pr-3 text-sm text-ink placeholder:text-muted focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/25"
        />
      </label>
      <ul className="grid">
        {modules.map((module) => {
          const containsCurrent = module.lessons.some((l) => l.id === currentId);
          const finished = module.total > 0 && module.completed === module.total;
          return (
            <li key={module.id} className="border-b border-line last:border-b-0">
              <details open={containsCurrent || Boolean(needle)} className="group">
                <summary className="flex min-h-14 cursor-pointer list-none items-center gap-3 px-1 py-2">
                  {finished ? (
                    <CheckCircle size={24} weight="fill" className="shrink-0 text-primary" aria-label="Módulo completado" />
                  ) : (
                    <Circle size={24} className="shrink-0 text-muted" aria-hidden />
                  )}
                  <span className="flex-1 font-semibold text-ink">{module.title}</span>
                  <span className="text-sm tabular-nums text-muted">
                    {module.completed} / {module.total}
                  </span>
                  <CaretDown size={16} weight="bold" className="text-muted transition duration-200 group-open:rotate-180" aria-hidden />
                </summary>
                <ol className="relative mb-2 ml-[0.7rem] grid border-l border-line">
                  {module.lessons.map((lesson) => {
                    const current = lesson.id === currentId;
                    return (
                      <li key={lesson.id} className="-ml-px">
                        <Link
                          to={`/a/${slug}/clases/${lesson.id}`}
                          onClick={onNavigate}
                          aria-current={current ? "page" : undefined}
                          className={`flex min-h-14 items-center gap-3 rounded-r-xl py-2 pl-0 pr-2 no-underline transition ${
                            current ? "bg-subtle" : "hover:bg-subtle/70"
                          }`}
                        >
                          <span className={`-ml-[0.45rem] grid size-3.5 shrink-0 place-items-center rounded-full ring-4 ring-bg ${lesson.completed ? "bg-primary" : current ? "bg-ink" : "bg-line"}`} aria-hidden />
                          <span className="min-w-0 flex-1">
                            <span className={`block truncate text-sm ${current ? "font-semibold text-ink" : "text-ink"}`}>{lesson.title}</span>
                            <span className="text-xs uppercase tracking-wide text-muted">
                              Video{lesson.duration_min ? ` · ${lesson.duration_min} min` : ""}
                            </span>
                          </span>
                          {lesson.completed && <CheckCircle size={18} weight="fill" className="shrink-0 text-primary" aria-label="Completada" />}
                          {!lesson.is_published && <Badge tone="alert">Borrador</Badge>}
                        </Link>
                      </li>
                    );
                  })}
                  {module.lessons.length === 0 && <li className="px-3 py-2 text-sm text-muted">Sin coincidencias.</li>}
                </ol>
              </details>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

// ── Player ───────────────────────────────────────────────────

function Player({ academy }: { academy: AcademyBranding }) {
  const { lessonId } = useParams();
  const { notify } = useNotifications();
  const [lesson, setLesson] = useState<LessonOut | null>(null);
  const [route, setRoute] = useState<RouteDetailOut | null>(null);
  const [error, setError] = useState<{ message: string; notFound: boolean } | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const current = await api<LessonOut>(`/lessons/${lessonId}`);
      const detail = await api<RouteDetailOut>(`/routes/${current.route_id}`);
      setLesson(current);
      setRoute(detail);
      setError(null);
    } catch (err) {
      setError({ message: errorMessage(err), notFound: err instanceof ApiError && err.status === 404 });
    }
  }, [lessonId]);

  useEffect(() => {
    void load();
    window.scrollTo({ top: 0 });
  }, [load]);

  const complete = useCallback(async () => {
    if (!lesson || lesson.completed) return;
    try {
      const result = await api<CompletionOut>(`/lessons/${lesson.id}/complete`, { method: "POST" });
      setLesson((current) => (current && current.id === lesson.id ? { ...current, completed: result.completed } : current));
      setRoute(await api<RouteDetailOut>(`/routes/${lesson.route_id}`)); // counters from the server
      notify({ id: `lesson-${lesson.id}`, title: "Clase completada", body: lesson.title });
    } catch (err) {
      notify({ id: `lesson-${lesson.id}-error`, tone: "warning", title: "No pudimos guardar tu avance", body: errorMessage(err) });
    }
  }, [lesson, notify]);

  if (error) {
    return (
      <>
        <TopBar academy={academy} />
        <div className="mx-auto max-w-xl p-6">
          {error.notFound ? (
            <EmptyState
              title="No encontramos esta clase"
              description="Puede que aún no esté publicada."
              mascotUrl={academy.mascot_url}
              action={<ButtonLink to={`/a/${academy.slug}/rutas`}>Ver rutas</ButtonLink>}
            />
          ) : (
            <ErrorState message={error.message} onRetry={() => void load()} />
          )}
        </div>
      </>
    );
  }
  if (!lesson || !route || String(lesson.id) !== lessonId) return <PlayerSkeleton />;

  const sidebar = (onNavigate?: () => void) => (
    <CourseSidebar route={route} currentId={lesson.id} slug={academy.slug} onNavigate={onNavigate} />
  );
  const navClass = (enabled: boolean) => (enabled ? "" : "pointer-events-none opacity-40");

  return (
    <>
      <TopBar academy={academy} title={route.title} />
      <div className="grid lg:grid-cols-[22rem_1fr]">
        <aside className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] overflow-y-auto border-r border-line bg-surface p-5 lg:block">
          {sidebar()}
        </aside>

        <article className="enter mx-auto grid w-full min-w-0 max-w-5xl content-start gap-5 p-4 sm:p-8" style={{ "--i": 0 } as CSSProperties}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="min-w-0 text-2xl sm:text-3xl">{lesson.title}</h1>
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="inline-flex min-h-11 items-center gap-2 rounded-full border border-line px-4 text-sm font-semibold text-ink hover:bg-subtle lg:hidden"
            >
              <ListBullets weight="bold" aria-hidden /> Contenido
            </button>
          </div>

          {!lesson.is_published && <Badge tone="alert">Vista previa: esta clase aún no está publicada</Badge>}

          <VideoFrame key={lesson.id} lesson={lesson} onEnded={() => void complete()} />

          <div className="flex flex-wrap items-center gap-3">
            <ButtonLink
              to={lesson.prev_lesson_id ? `/a/${academy.slug}/clases/${lesson.prev_lesson_id}` : "#"}
              variant="secondary"
              aria-disabled={!lesson.prev_lesson_id}
              className={navClass(Boolean(lesson.prev_lesson_id))}
              icon={<ArrowLeft weight="bold" />}
            >
              Anterior
            </ButtonLink>
            <p role="status" className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 text-sm text-muted sm:flex-none">
              {lesson.completed ? (
                <>
                  <CheckCircle size={20} weight="fill" className="text-primary" aria-hidden />
                  <span className="font-semibold text-ink">Clase completada</span>
                </>
              ) : (
                <>
                  <PlayCircle size={20} aria-hidden /> Se marca como completada al terminar el video
                </>
              )}
            </p>
            <ButtonLink
              to={lesson.next_lesson_id ? `/a/${academy.slug}/clases/${lesson.next_lesson_id}` : "#"}
              variant={lesson.completed ? "primary" : "secondary"}
              aria-disabled={!lesson.next_lesson_id}
              className={`sm:ml-auto ${navClass(Boolean(lesson.next_lesson_id))}`}
            >
              Siguiente <ArrowRight weight="bold" aria-hidden />
            </ButtonLink>
          </div>

          <section aria-labelledby="descripcion" className="border-t border-line pt-6">
            <h2 id="descripcion" className="mb-3 text-xl">
              Descripción
            </h2>
            {lesson.description ? <Markdown source={lesson.description} /> : <p className="text-muted">Esta clase no tiene descripción.</p>}
          </section>

          {lesson.links.length > 0 && (
            <section aria-labelledby="recursos-clase" className="border-t border-line pt-6">
              <h2 id="recursos-clase" className="mb-3 text-xl">
                Recursos de la clase
              </h2>
              <ul className="grid gap-2 sm:grid-cols-2">
                {lesson.links.map((link) => (
                  <li key={link.id}>
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer nofollow"
                      className="flex min-h-12 items-center gap-2 rounded-xl border border-line bg-surface px-4 font-medium no-underline transition hover:bg-subtle"
                    >
                      <LinkSimple weight="bold" aria-hidden /> {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </article>
      </div>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Contenido de la ruta">
        {sidebar(() => setDrawerOpen(false))}
      </Drawer>
    </>
  );
}
