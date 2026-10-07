// Flow step 3 (UPS-007): learning routes and the course player.
//   /a/:slug/rutas                 → routes of the academy
//   /a/:slug/rutas/:routeId        → resume the route (next unfinished lesson)
//   /a/:slug/clases/:lessonId      → player
import {
  ArrowLeft,
  ArrowRight,
  CaretDown,
  CheckCircle,
  Circle,
  ListBullets,
  LinkSimple,
  MagnifyingGlass,
  PlayCircle,
  WifiSlash,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams, type RouteObject } from "react-router";

import { Badge } from "@/components/Badge";
import { Button, ButtonLink } from "@/components/Button";
import { Card } from "@/components/Card";
import { Markdown } from "@/components/Markdown";
import { Drawer } from "@/components/Overlay";
import { ProgressBar } from "@/components/ProgressBar";
import { PageSkeleton, Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, ApiError, errorMessage } from "@/lib/api";
import { RequireRole } from "@/lib/auth";
import type { LessonOut, Page, RouteCardOut, RouteDetailOut, RouteProgressOut } from "@/lib/types";
import { AcademyLayout, useAcademy } from "@/layouts";

export const order = 40;

interface CompletionOut {
  lesson_id: number;
  completed: boolean;
  progress: RouteProgressOut;
}

const VIDEO_TIMEOUT_MS = 8000;

// ── Routes list ──────────────────────────────────────────────

function RoutesPage() {
  const academy = useAcademy();
  const [routes, setRoutes] = useState<RouteCardOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      api<Page<RouteCardOut>>(`/academies/${academy.slug}/routes`, { query: { limit: 50 } })
        .then((page) => setRoutes(page.items))
        .catch((err) => setError(errorMessage(err))),
    [academy.slug],
  );
  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!routes) return <PageSkeleton />;

  return (
    <div>
      <h1 className="mb-2 text-3xl sm:text-4xl">Rutas de aprendizaje</h1>
      <p className="mb-8 text-muted">Cada ruta tiene módulos y clases en video. Tu avance se guarda solo.</p>
      {routes.length === 0 ? (
        <EmptyState title="Aún no hay rutas publicadas" mascotUrl={academy.mascot_url} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {routes.map((route) => (
            <Link key={route.id} to={`/a/${academy.slug}/rutas/${route.id}`} className="no-underline">
              <Card stripe interactive className="grid h-full gap-3 p-6">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-2xl">{route.title}</h2>
                  {!route.is_published && <Badge tone="alert">Borrador</Badge>}
                </div>
                {route.description && <p className="text-muted">{route.description}</p>}
                {route.progress && (
                  <>
                    <ProgressBar percent={route.progress.percent} label={`Progreso de ${route.title}`} />
                    <span className="inline-flex items-center gap-1 font-semibold text-link">
                      {route.progress.completed === 0 ? "Empezar" : route.progress.percent === 100 ? "Repasar" : "Continuar"}
                      <ArrowRight weight="bold" aria-hidden />
                    </span>
                  </>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Route → resume ───────────────────────────────────────────

function RouteResume() {
  const academy = useAcademy();
  const { routeId } = useParams();
  const [target, setTarget] = useState<number | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<RouteDetailOut>(`/routes/${routeId}`)
      .then((route) => {
        const first = route.modules.flatMap((m) => m.lessons)[0]?.id ?? null;
        setTarget(route.progress?.next_lesson_id ?? first);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [routeId]);

  if (error) return <ErrorState message={error} />;
  if (target === undefined) return <PageSkeleton />;
  if (target === null) return <EmptyState title="Esta ruta aún no tiene clases" mascotUrl={academy.mascot_url} />;
  return <Navigate to={`/a/${academy.slug}/clases/${target}`} replace />;
}

// ── Player ───────────────────────────────────────────────────

function VideoFrame({ lesson }: { lesson: LessonOut }) {
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable">(() =>
    typeof navigator !== "undefined" && !navigator.onLine ? "unavailable" : "loading",
  );

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
      className="relative aspect-video w-full overflow-hidden rounded-2xl bg-video bg-cover bg-center shadow-soft"
      style={{ backgroundImage: `url("${lesson.thumbnail_url}")` }}
    >
      {status !== "unavailable" && (
        <iframe
          className="absolute inset-0 size-full"
          src={`${lesson.embed_url}?rel=0&modestbranding=1`}
          title={lesson.title}
          loading="lazy"
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

  return (
    <nav aria-label="Contenido de la ruta" className="grid gap-4">
      <div>
        <h2 className="text-xl">{route.title}</h2>
        {route.progress && (
          <div className="mt-2">
            <ProgressBar percent={route.progress.percent} label="Progreso de la ruta" />
            <p className="mt-1 text-xs text-muted">
              {route.progress.completed} de {route.progress.total} clases completadas
            </p>
          </div>
        )}
      </div>
      <label className="relative block">
        <span className="sr-only">Buscar por el título de la lección</span>
        <MagnifyingGlass size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar por el título de la lección"
          className="w-full rounded-[var(--radius-field)] border border-line bg-surface py-2.5 pl-10 pr-3 text-sm focus:border-secondary focus:outline-none focus:ring-3 focus:ring-primary/25"
        />
      </label>
      <ul className="grid gap-2">
        {modules.map((module) => {
          const containsCurrent = module.lessons.some((l) => l.id === currentId);
          const finished = module.total > 0 && module.completed === module.total;
          return (
            <li key={module.id}>
              <details open={containsCurrent || Boolean(needle)} className="group rounded-2xl border border-line bg-surface">
                <summary className="flex min-h-12 cursor-pointer list-none items-center gap-3 px-3 py-2">
                  {finished ? (
                    <CheckCircle size={22} weight="fill" className="shrink-0 text-primary" aria-label="Módulo completado" />
                  ) : (
                    <Circle size={22} weight="bold" className="shrink-0 text-line" aria-hidden />
                  )}
                  <span className="flex-1 font-semibold text-ink">{module.title}</span>
                  <span className="text-sm tabular-nums text-muted">
                    {module.completed} / {module.total}
                  </span>
                  <CaretDown size={16} weight="bold" className="text-muted transition group-open:rotate-180" aria-hidden />
                </summary>
                <ol className="grid gap-0.5 border-t border-line p-1.5">
                  {module.lessons.map((lesson) => {
                    const current = lesson.id === currentId;
                    return (
                      <li key={lesson.id}>
                        <Link
                          to={`/a/${slug}/clases/${lesson.id}`}
                          onClick={onNavigate}
                          aria-current={current ? "page" : undefined}
                          className={`flex min-h-11 items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm no-underline ${
                            current ? "bg-primary/15 font-semibold text-ink ring-1 ring-primary/40" : "text-ink hover:bg-line/40"
                          }`}
                        >
                          {lesson.completed ? (
                            <CheckCircle size={18} weight="fill" className="shrink-0 text-primary" aria-label="Completada" />
                          ) : (
                            <PlayCircle size={18} weight={current ? "fill" : "regular"} className="shrink-0 text-secondary" aria-hidden />
                          )}
                          <span className="flex-1">{lesson.title}</span>
                          {!lesson.is_published && <Badge tone="alert">Borrador</Badge>}
                          {lesson.duration_min && <span className="text-xs text-muted">{lesson.duration_min} min</span>}
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

function PlayerPage() {
  const academy = useAcademy();
  const { lessonId } = useParams();
  const navigate = useNavigate();
  const [lesson, setLesson] = useState<LessonOut | null>(null);
  const [route, setRoute] = useState<RouteDetailOut | null>(null);
  const [error, setError] = useState<{ message: string; notFound: boolean } | null>(null);
  const [saving, setSaving] = useState(false);
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

  async function toggleComplete() {
    if (!lesson) return;
    setSaving(true);
    try {
      const result = await api<CompletionOut>(`/lessons/${lesson.id}/complete`, {
        method: lesson.completed ? "DELETE" : "POST",
      });
      setLesson({ ...lesson, completed: result.completed });
      // Refresh the sidebar counters and the route progress bar from the server (source of truth).
      setRoute(await api<RouteDetailOut>(`/routes/${lesson.route_id}`));
      if (result.completed && lesson.next_lesson_id) {
        // Keep the learner moving: completing jumps to the next lesson.
        navigate(`/a/${academy.slug}/clases/${lesson.next_lesson_id}`);
      }
    } catch (err) {
      setError({ message: errorMessage(err), notFound: false });
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return error.notFound ? (
      <EmptyState
        title="No encontramos esta clase"
        description="Puede que aún no esté publicada."
        mascotUrl={academy.mascot_url}
        action={<ButtonLink to={`/a/${academy.slug}/rutas`}>Ver rutas</ButtonLink>}
      />
    ) : (
      <ErrorState message={error.message} onRetry={() => void load()} />
    );
  }
  if (!lesson || !route || String(lesson.id) !== lessonId) {
    return (
      <div className="grid gap-6 lg:grid-cols-[20rem_1fr]">
        <Skeleton className="hidden h-96 lg:block" />
        <div className="grid gap-4">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="aspect-video w-full" />
        </div>
      </div>
    );
  }

  const sidebar = (onNavigate?: () => void) => (
    <CourseSidebar route={route} currentId={lesson.id} slug={academy.slug} onNavigate={onNavigate} />
  );

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[20rem_1fr]">
      <aside className="sticky top-24 hidden max-h-[calc(100dvh-7rem)] overflow-y-auto rounded-card border border-line bg-surface p-4 shadow-soft lg:block">
        {sidebar()}
      </aside>

      <article className="grid min-w-0 gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-link">{route.title}</p>
            <h1 className="text-2xl sm:text-3xl">{lesson.title}</h1>
          </div>
          <Button variant="secondary" size="sm" className="lg:hidden" icon={<ListBullets weight="bold" />} onClick={() => setDrawerOpen(true)}>
            Contenido
          </Button>
        </div>

        {!lesson.is_published && <Badge tone="alert">Vista previa: esta clase aún no está publicada</Badge>}

        <VideoFrame key={lesson.id} lesson={lesson} />

        <div className="flex flex-wrap items-center gap-3">
          <ButtonLink
            to={lesson.prev_lesson_id ? `/a/${academy.slug}/clases/${lesson.prev_lesson_id}` : "#"}
            variant="secondary"
            aria-disabled={!lesson.prev_lesson_id}
            className={lesson.prev_lesson_id ? "" : "pointer-events-none opacity-50"}
            icon={<ArrowLeft weight="bold" />}
          >
            Anterior
          </ButtonLink>
          <Button
            variant={lesson.completed ? "secondary" : "primary"}
            loading={saving}
            onClick={toggleComplete}
            icon={<CheckCircle weight={lesson.completed ? "fill" : "bold"} />}
            className="flex-1 sm:flex-none"
          >
            {lesson.completed ? "Completada · desmarcar" : "Marcar como completada"}
          </Button>
          <ButtonLink
            to={lesson.next_lesson_id ? `/a/${academy.slug}/clases/${lesson.next_lesson_id}` : "#"}
            variant="secondary"
            aria-disabled={!lesson.next_lesson_id}
            className={`sm:ml-auto ${lesson.next_lesson_id ? "" : "pointer-events-none opacity-50"}`}
          >
            Siguiente <ArrowRight weight="bold" aria-hidden />
          </ButtonLink>
        </div>

        <section aria-labelledby="descripcion" className="rounded-card border border-line bg-surface p-5 sm:p-6">
          <h2 id="descripcion" className="mb-2 text-xl">
            Descripción
          </h2>
          {lesson.description ? <Markdown source={lesson.description} /> : <p className="text-muted">Esta clase no tiene descripción.</p>}
        </section>

        {lesson.links.length > 0 && (
          <section aria-labelledby="recursos-clase" className="rounded-card border border-line bg-surface p-5 sm:p-6">
            <h2 id="recursos-clase" className="mb-3 text-xl">
              Recursos de la clase
            </h2>
            <ul className="grid gap-2">
              {lesson.links.map((link) => (
                <li key={link.id}>
                  <a href={link.url} target="_blank" rel="noopener noreferrer nofollow" className="inline-flex items-center gap-2 font-medium">
                    <LinkSimple weight="bold" aria-hidden /> {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}
      </article>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Contenido de la ruta">
        {sidebar(() => setDrawerOpen(false))}
      </Drawer>
    </div>
  );
}

export const routes: RouteObject[] = [
  {
    path: "/a/:slug",
    element: (
      <RequireRole>
        <AcademyLayout />
      </RequireRole>
    ),
    children: [
      { path: "rutas", element: <RoutesPage /> },
      { path: "rutas/:routeId", element: <RouteResume /> },
      { path: "clases/:lessonId", element: <PlayerPage /> },
    ],
  },
];
