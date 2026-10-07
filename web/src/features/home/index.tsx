// Flow step 2 (UPS-006): UpiixSol campus home + academies list.
import { ArrowRight, CalendarBlank, ChatsCircle, CheckCircle, Sparkle } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { Link, type RouteObject } from "react-router";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Button, ButtonLink } from "@/components/Button";
import { Card, SectionTitle } from "@/components/Card";
import { CardSkeleton, PageSkeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import { AcademyTheme, safeAssetPath } from "@/lib/theme";
import type { AcademyCardOut, EventOut, HomeContentOut, Page, PostOut } from "@/lib/types";
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

export function AcademyCard({ academy }: { academy: AcademyCardOut }) {
  const logo = safeAssetPath(academy.logo_url);
  return (
    <AcademyTheme branding={academy}>
      <Link to={`/a/${academy.slug}`} className="block h-full no-underline" aria-label={`Entrar a ${academy.name}`}>
        <Card stripe interactive className="flex h-full flex-col gap-3 p-5">
          <div className="flex items-start justify-between gap-2">
            {logo ? <img src={logo} alt="" className="h-9 w-auto" loading="lazy" /> : <span className="font-display text-2xl font-bold text-ink">{academy.name}</span>}
            {academy.is_enrolled && (
              <Badge tone="primary" icon={<CheckCircle weight="bold" />}>
                Inscrito
              </Badge>
            )}
          </div>
          <h3 className="text-xl">{academy.name}</h3>
          <p className="flex-1 text-sm text-muted">{academy.short_description}</p>
          <span className="inline-flex items-center gap-1 font-semibold text-link">
            Entrar <ArrowRight weight="bold" aria-hidden />
          </span>
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
        <p className="text-sm capitalize text-muted">{formatDate(event.starts_at)}</p>
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

function HomePage() {
  const { user } = useAuth();
  const { data, error, loading, retry } = useData<HomeOut>("/home");

  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState message={error ?? "No pudimos cargar el inicio."} onRetry={retry} />;

  return (
    <div className="grid gap-10">
      <section className="grid items-center gap-6 overflow-hidden rounded-card border border-line bg-surface p-6 shadow-soft sm:p-10 lg:grid-cols-[1.3fr_1fr]">
        <div>
          <p className="mb-2 inline-flex items-center gap-1.5 text-sm font-semibold text-link">
            <Sparkle weight="fill" aria-hidden /> ¡Hola, {user?.nickname}!
          </p>
          <h1 className="text-3xl sm:text-5xl">{data.hero?.hero_title ?? "Bienvenido a UpiixSol Campus"}</h1>
          {data.hero?.hero_text && <p className="mt-4 max-w-xl text-lg text-muted">{data.hero.hero_text}</p>}
          <div className="mt-6 flex flex-wrap gap-3">
            <ButtonLink to="/academias" size="lg">
              Explorar academias
            </ButtonLink>
            <ButtonLink to="/comunidad" size="lg" variant="secondary" icon={<ChatsCircle weight="bold" />}>
              Comunidad
            </ButtonLink>
          </div>
        </div>
        <img src="/brand/upiixsol/mascot.png" alt="Ajolote de UpiixSol" className="mx-auto w-full max-w-sm rounded-card" />
      </section>

      <section aria-labelledby="academias">
        <SectionTitle title="Academias" subtitle="Elige una y entra: todo el campus toma su identidad." action={<Link to="/academias">Ver todas</Link>} />
        {data.academies.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.academies.map((academy) => (
              <AcademyCard key={academy.id} academy={academy} />
            ))}
          </div>
        ) : (
          <EmptyState title="Aún no hay academias" description="La mesa directiva está preparando las primeras." />
        )}
      </section>

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
          <SectionTitle title="Actividad de la comunidad" action={<Link to="/comunidad">Ir a la comunidad</Link>} />
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

function AcademiesPage() {
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
      <h1 className="mb-2 text-3xl sm:text-4xl">Academias</h1>
      <p className="mb-8 text-muted">Todas las academias activas del club. Entra a cualquiera; inscríbete para seguir tu progreso.</p>
      {state === "loading" ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
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
        <EmptyState title="Aún no hay academias" />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
      { path: "/academias", element: <AcademiesPage /> },
    ],
  },
];
