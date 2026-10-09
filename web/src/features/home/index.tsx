// Flow step 2 (UPS-006): campus home + clubs list.
import { ArrowRight, CalendarBlank, CheckCircle, PlayCircle, Sparkle } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, type RouteObject } from "react-router";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Button, ButtonLink } from "@/components/Button";
import { Card, SectionTitle } from "@/components/Card";
import { ProgressBar } from "@/components/ProgressBar";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import { LOGO_HEIGHT, SITE, Wordmark } from "@/lib/brand";
import { AcademyTheme, safeAssetPath } from "@/lib/theme";
import type { AcademyCardOut, ContinueOut, EventOut, HomeContentOut, Page, PostOut } from "@/lib/types";
import { CampusLayout } from "@/layouts";

export const order = 20;

interface ProjectCardOut {
  id: number;
  title: string;
  slug: string;
  summary: string;
  cover_url: string | null;
}

interface HomeOut {
  hero: HomeContentOut | null;
  academies: AcademyCardOut[];
  featured_projects: ProjectCardOut[];
  upcoming_events: EventOut[];
  recent_activity: PostOut[];
}

const dateFormat = new Intl.DateTimeFormat("es-MX", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
const relative = new Intl.RelativeTimeFormat("es-MX", { numeric: "auto" });

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

export function timeAgo(iso: string): string {
  const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60_000);
  if (Math.abs(minutes) < 60) return relative.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return relative.format(hours, "hour");
  return relative.format(Math.round(hours / 24), "day");
}

/** Plain-text excerpt of a markdown/HTML body for previews (rendered as text, never as HTML). */
export function excerpt(body: string, max = 140): string {
  const text = body.replace(/<[^>]*>/g, "").replace(/[*_#>`]/g, "").replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function useData<T>(path: string) {
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>({ data: null, error: null, loading: true });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    api<T>(path)
      .then((data) => active && setState({ data, error: null, loading: false }))
      .catch((err) => active && setState({ data: null, error: errorMessage(err), loading: false }));
    return () => {
      active = false;
    };
  }, [path, attempt]);
  return { ...state, retry: useCallback(() => setAttempt((n) => n + 1), []) };
}

/**
 * Club card in the club's colors. With a logo: logo band + name heading. Without one, the band shows the
 * name as a wordmark and that wordmark is the heading, so the name never shows twice.
 */
export function AcademyCard({ academy }: { academy: AcademyCardOut }) {
  const logo = safeAssetPath(academy.logo_url);
  const badge = academy.is_enrolled && (
    <Badge tone="primary" icon={<CheckCircle weight="bold" />}>
      Miembro
    </Badge>
  );
  return (
    <AcademyTheme branding={academy} className="min-w-0">
      <Link to={`/a/${academy.slug}`} className="block h-full no-underline" aria-label={`Entrar a ${academy.name}`}>
        <Card interactive className="flex h-full flex-col">
          <div className="flex min-h-24 items-center justify-center bg-primary/10 px-5 py-4">
            {logo ? (
              <img src={logo} alt="" className={`max-h-(--logo-h) w-auto ${LOGO_HEIGHT.card}`} loading="lazy" />
            ) : (
              <h3 className="min-w-0 max-w-full text-center">
                <Wordmark name={academy.name} colors={academy} className={`line-clamp-2 break-words ${LOGO_HEIGHT.card}`} />
              </h3>
            )}
          </div>
          <div aria-hidden className="h-1 bg-primary" />
          <div className="flex flex-1 flex-col gap-2 p-5">
            {logo ? (
              <div className="flex items-start justify-between gap-2">
                <h3 className="min-w-0 break-words text-xl">{academy.name}</h3>
                {badge}
              </div>
            ) : (
              badge && <div className="self-start">{badge}</div>
            )}
            <p className="text-sm text-muted">{academy.short_description || "Rutas, recursos y comunidad del club."}</p>
            <span className="mt-auto inline-flex items-center gap-1 pt-1 font-semibold text-link">
              Entrar <ArrowRight weight="bold" aria-hidden />
            </span>
          </div>
        </Card>
      </Link>
    </AcademyTheme>
  );
}

export function EventItem({ event }: { event: EventOut }) {
  return (
    <li className="flex gap-3">
      <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-accent/20 text-ink">
        <CalendarBlank size={22} weight="bold" aria-hidden />
      </div>
      <div className="min-w-0">
        <p className="font-semibold text-ink">{event.title}</p>
        <p className="text-sm text-muted first-letter:uppercase">{formatDate(event.starts_at)}</p>
        {event.location && <p className="truncate text-sm text-muted">{event.location}</p>}
      </div>
    </li>
  );
}

export function PostPreview({ post }: { post: PostOut }) {
  return (
    <li className="flex gap-3">
      <Avatar user={post.author} size="sm" />
      <div className="min-w-0">
        <p className="text-sm">
          <span className="font-semibold text-ink">{post.author.nickname}</span>{" "}
          <span className="text-muted">
            en #{post.channel_slug} · {timeAgo(post.created_at)}
          </span>
        </p>
        <p className="text-sm text-ink">{excerpt(post.body)}</p>
      </div>
    </li>
  );
}

interface ClubHomeLite {
  academy: AcademyCardOut;
  continue: ContinueOut | null;
}

/** Same silhouette as ContinueCard so the block does not jump when it resolves. */
function ContinueSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label="Cargando tu avance">
      {[0, 1, 2].map((i) => (
        <div key={i} className="rounded-card border border-line bg-surface p-5 shadow-soft">
          <Skeleton className="mb-3 h-8 w-24" />
          <Skeleton className="mb-2 h-5 w-4/5" />
          <Skeleton className="mb-4 h-3 w-full" />
          <Skeleton className="h-10 w-32 rounded-full" />
        </div>
      ))}
    </div>
  );
}

function ContinueTile({ club }: { club: ClubHomeLite }) {
  const info = club.continue as ContinueOut;
  const logo = safeAssetPath(club.academy.logo_url);
  const done = info.percent === 100;
  return (
    <AcademyTheme branding={club.academy} className="min-w-0">
      <Card interactive className="flex h-full flex-col gap-3 p-5">
        {logo ? (
          <img src={logo} alt={club.academy.name} className={`h-(--logo-h) w-auto self-start ${LOGO_HEIGHT.tile}`} loading="lazy" />
        ) : (
          <Wordmark name={club.academy.name} colors={club.academy} className={`block max-w-full self-start truncate ${LOGO_HEIGHT.tile}`} />
        )}
        <p className="text-lg font-semibold text-ink">
          Clase {info.lesson_number} · {info.lesson_title}
        </p>
        <ProgressBar percent={info.percent} label={`Progreso en ${club.academy.name}`} />
        <ButtonLink to={`/a/${club.academy.slug}/clases/${info.lesson_id}`} className="mt-auto self-start" icon={<PlayCircle weight="fill" />}>
          {done ? "Repasar" : "Continuar"}
        </ButtonLink>
      </Card>
    </AcademyTheme>
  );
}

function ContinueLearning({ clubs }: { clubs: AcademyCardOut[] }) {
  const [items, setItems] = useState<ClubHomeLite[] | null>(null);
  const enrolled = clubs.filter((c) => c.is_enrolled).slice(0, 6);
  const key = enrolled.map((c) => c.slug).join(",");

  useEffect(() => {
    let active = true;
    const list = key ? key.split(",") : [];
    Promise.all(list.map((slug) => api<ClubHomeLite>(`/academies/${slug}/home`).catch(() => null))).then((all) => {
      if (active) setItems(all.filter((c): c is ClubHomeLite => !!c && !!c.continue));
    });
    return () => {
      active = false;
    };
  }, [key]);

  return (
    <section aria-labelledby="continuar">
      <h2 id="continuar" className="mb-4 text-2xl">
        Continúa aprendiendo
      </h2>
      {items === null && enrolled.length > 0 ? (
        <ContinueSkeleton />
      ) : items && items.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((club) => (
            <ContinueTile key={club.academy.id} club={club} />
          ))}
        </div>
      ) : (
        <Card className="flex flex-wrap items-center justify-between gap-3 p-5">
          <p className="text-muted">Cuando empieces una clase, aquí retomas justo donde te quedaste.</p>
          <ButtonLink to="/clubes" variant="secondary">
            Ver clubes
          </ButtonLink>
        </Card>
      )}
    </section>
  );
}

function ListSkeleton({ rows }: { rows: number }) {
  return (
    <div className="grid gap-4" aria-hidden>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex gap-3">
          <Skeleton className="size-12 shrink-0 rounded-2xl" />
          <div className="flex-1">
            <Skeleton className="mb-2 h-4 w-3/5" />
            <Skeleton className="h-3 w-2/5" />
          </div>
        </div>
      ))}
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div role="status" aria-label="Cargando inicio" className="grid gap-10">
      <div className="grid items-center gap-6 rounded-card border border-line bg-surface p-6 shadow-soft sm:p-10 lg:grid-cols-[1.3fr_1fr]">
        <div>
          <Skeleton className="mb-3 h-4 w-32" />
          <Skeleton className="mb-3 h-12 w-4/5" />
          <Skeleton className="h-5 w-3/5" />
        </div>
        <Skeleton className="mx-auto hidden h-40 w-full max-w-xs lg:block" />
      </div>
      <ContinueSkeleton />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-card border border-line bg-surface p-6 shadow-soft">
          <Skeleton className="mb-5 h-7 w-44" />
          <ListSkeleton rows={3} />
        </div>
        <div className="rounded-card border border-line bg-surface p-6 shadow-soft">
          <Skeleton className="mb-5 h-7 w-44" />
          <ListSkeleton rows={3} />
        </div>
      </div>
    </div>
  );
}

function HomePage() {
  const { user } = useAuth();
  const { data, error, loading, retry } = useData<HomeOut>("/home");

  if (loading) return <HomeSkeleton />;
  if (error || !data) return <ErrorState message={error ?? "No pudimos cargar el inicio."} onRetry={retry} />;

  // The superadmin's text always wins (the seed copy says "clubs" since UPS-027).
  const heroText = data.hero?.hero_text || "Retoma tus clases donde te quedaste y conversa con tu comunidad.";

  return (
    <div className="grid grid-cols-1 gap-10">
      <section className="grid items-center gap-6 overflow-hidden rounded-card border border-line bg-surface p-6 shadow-soft sm:p-10 lg:grid-cols-[1.3fr_1fr]">
        <div>
          <p className="mb-2 inline-flex items-center gap-1.5 text-sm font-semibold text-link">
            <Sparkle weight="fill" aria-hidden /> ¡Hola, {user?.nickname}!
          </p>
          <h1 className="text-3xl sm:text-5xl">Tus clubs en un solo campus</h1>
          <p className="mt-4 max-w-xl text-lg text-muted">
            {heroText}
          </p>
        </div>
        <img src={SITE.mascotUrl} alt={`Mascota de ${SITE.name}`} className="mx-auto w-full max-w-xs" />
      </section>

      <ContinueLearning clubs={data.academies} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <SectionTitle title="Próximos eventos" action={<Link to="/calendario">Calendario</Link>} />
          {data.upcoming_events.length ? (
            <ul className="grid gap-4">
              {data.upcoming_events.map((event) => (
                <EventItem key={event.id} event={event} />
              ))}
            </ul>
          ) : (
            <p className="text-muted">No hay eventos próximos.</p>
          )}
        </Card>
        <Card className="p-6">
          <SectionTitle title="Últimas publicaciones" action={<Link to="/comunidad">Ir a la comunidad</Link>} />
          {data.recent_activity.length ? (
            <ul className="grid gap-4">
              {data.recent_activity.map((post) => (
                <PostPreview key={post.id} post={post} />
              ))}
            </ul>
          ) : (
            <p className="text-muted">Sé la primera persona en publicar.</p>
          )}
        </Card>
      </div>

      <section aria-labelledby="clubes">
        <SectionTitle title="Clubes" subtitle="Elige uno y entra: el campus toma su identidad." action={<Link to="/clubes">Ver todos</Link>} />
        {data.academies.length ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.academies.map((academy) => (
              <AcademyCard key={academy.id} academy={academy} />
            ))}
          </div>
        ) : (
          <EmptyState title="Aún no hay clubes" description="La mesa directiva está preparando los primeros." />
        )}
      </section>

      {data.featured_projects.length > 0 && (
        <section aria-labelledby="proyectos">
          <SectionTitle title="Proyectos destacados" action={<Link to="/galeria">Ver galería</Link>} />
          <div className="grid gap-4 sm:grid-cols-2">
            {data.featured_projects.map((project) => (
              <Link key={project.id} to={`/galeria/${project.slug}`} className="no-underline">
                <Card interactive className="h-full p-5">
                  <h3 className="text-lg">{project.title}</h3>
                  <p className="mt-1 text-sm text-muted">{project.summary}</p>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ClubCardSkeleton() {
  return (
    <div role="status" aria-label="Cargando club" className="overflow-hidden rounded-card border border-line bg-surface shadow-soft">
      <Skeleton className="h-24 w-full rounded-none" />
      <div className="p-5">
        <Skeleton className="mb-3 h-6 w-2/3" />
        <Skeleton className="mb-2 h-4 w-full" />
        <Skeleton className="mb-4 h-4 w-4/5" />
        <Skeleton className="h-5 w-16" />
      </div>
    </div>
  );
}

function ClubsPage() {
  const [items, setItems] = useState<AcademyCardOut[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "more" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (after: string | null) => {
    try {
      const page = await api<Page<AcademyCardOut>>("/academies", { query: { cursor: after, limit: 24 } });
      setItems((prev) => (after ? [...prev, ...page.items] : page.items));
      setCursor(page.next_cursor);
      setState("ready");
    } catch (err) {
      setError(errorMessage(err));
      setState("error");
    }
  }, []);

  useEffect(() => {
    void load(null);
  }, [load]);

  return (
    <div>
      <h1 className="mb-2 text-3xl sm:text-4xl">Clubes</h1>
      <p className="mb-8 text-muted">Todos los clubes activos del campus. Entra a cualquiera y sigue tu progreso.</p>
      {state === "loading" ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <ClubCardSkeleton />
          <ClubCardSkeleton />
          <ClubCardSkeleton />
        </div>
      ) : state === "error" ? (
        <ErrorState
          message={error ?? ""}
          onRetry={() => {
            setState("loading");
            void load(null);
          }}
        />
      ) : items.length === 0 ? (
        <EmptyState title="Aún no hay clubes" description="La mesa directiva está preparando los primeros." />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((academy) => (
              <AcademyCard key={academy.id} academy={academy} />
            ))}
          </div>
          {cursor && (
            <div className="mt-6 text-center">
              <Button
                variant="secondary"
                loading={state === "more"}
                onClick={() => {
                  setState("more");
                  void load(cursor);
                }}
              >
                Ver más
              </Button>
            </div>
          )}
        </>
      )}
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
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/clubes", element: <ClubsPage /> },
      { path: "/academias", element: <Navigate to="/clubes" replace /> },
    ],
  },
];
