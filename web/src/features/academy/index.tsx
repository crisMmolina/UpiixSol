// Club home (UPS-006, redesign UPS-023): "Continúa aprendiendo" route tiles, resources, latest posts
// of its channel and upcoming events; plus the route catalog at /a/:slug/rutas.
import { ArrowRight, BookOpenText, FileText, LinkSimple, VideoCamera } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { Link, type RouteObject } from "react-router";

import { Card, SectionTitle } from "@/components/Card";
import { Markdown } from "@/components/Markdown";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import { RequireRole } from "@/lib/auth";
import { safeAssetPath } from "@/lib/theme";
import type { AcademyOut, ContinueOut, EventOut, Page, PostOut, ResourceOut, ResourceType, RouteCardOut } from "@/lib/types";
import { AcademyLayout, useAcademy } from "@/layouts";

import { EventItem, PostPreview } from "../home";
import { RouteGridSkeleton, RouteTile, routeStatus } from "./RouteTile";

export const order = 30;

interface AcademyHomeOut {
  academy: AcademyOut;
  is_enrolled: boolean;
  continue: ContinueOut | null;
  routes: RouteCardOut[];
  recent_resources: ResourceOut[];
  latest_posts: PostOut[];
  upcoming_events: EventOut[];
}

/** In-progress routes first, then not started, then finished. */
function sortForLearning(list: RouteCardOut[]): RouteCardOut[] {
  const rank = { Continuar: 0, Iniciar: 1, Repasar: 2 } as const;
  return [...list].sort((a, b) => rank[routeStatus(a)] - rank[routeStatus(b)] || a.position - b.position);
}

function HomeSkeleton() {
  return (
    <div role="status" aria-label="Cargando" className="grid gap-8">
      <div className="grid items-center gap-6 rounded-card border border-line bg-surface p-6 shadow-soft sm:p-8 md:grid-cols-[1fr_auto]">
        <div className="grid gap-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-10 w-72 max-w-full" />
          <Skeleton className="h-5 w-full max-w-xl" />
        </div>
        <Skeleton className="mx-auto size-40 rounded-card" />
      </div>
      <section>
        <Skeleton className="mb-4 h-7 w-56" />
        <RouteGridSkeleton />
      </section>
      <div className="grid gap-6 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-card border border-line bg-surface p-6 shadow-soft">
            <Skeleton className="mb-4 h-6 w-40" />
            <Skeleton className="mb-2 h-4 w-full" />
            <Skeleton className="mb-2 h-4 w-5/6" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}

function RoutesCatalog() {
  const academy = useAcademy();
  const [routes, setRoutes] = useState<RouteCardOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      api<Page<RouteCardOut>>(`/academies/${academy.slug}/routes`, { query: { limit: 50 } })
        .then((page) => {
          setRoutes(page.items);
          setError(null);
        })
        .catch((err) => setError(errorMessage(err))),
    [academy.slug],
  );
  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div>
      <h1 className="mb-2 text-3xl sm:text-4xl">Rutas de aprendizaje</h1>
      <p className="mb-8 text-muted">Cada ruta tiene módulos y clases en video. Tu avance se guarda solo.</p>
      {error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : !routes ? (
        <RouteGridSkeleton count={6} />
      ) : routes.length === 0 ? (
        <EmptyState title="Aún no hay rutas publicadas" mascotUrl={safeAssetPath(academy.mascot_url)} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {routes.map((route, index) => (
            <RouteTile key={route.id} slug={academy.slug} route={route} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}

const resourceIcon: Record<ResourceType, typeof FileText> = {
  document: FileText,
  link: LinkSimple,
  video: VideoCamera,
  other: BookOpenText,
};

function AcademyHome() {
  const branding = useAcademy();
  const [data, setData] = useState<AcademyHomeOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      api<AcademyHomeOut>(`/academies/${branding.slug}/home`)
        .then((home) => {
          setData(home);
          setError(null);
        })
        .catch((err) => setError(errorMessage(err))),
    [branding.slug],
  );

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!data) return <HomeSkeleton />;

  const mascot = safeAssetPath(branding.mascot_url);
  return (
    <div className="grid gap-8">
      <section className="grid items-center gap-6 rounded-card border border-line bg-surface p-6 shadow-soft sm:p-8 md:grid-cols-[1fr_auto]">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-link">Bienvenida al club</p>
          {/* A name that is one long word wraps inside the card instead of pushing the page sideways. */}
          <h1 className="mt-1 break-words text-3xl sm:text-4xl">{data.academy.name}</h1>
          {data.academy.welcome_text && <Markdown source={data.academy.welcome_text} className="mt-3 max-w-2xl text-lg" />}
        </div>
        {mascot && <img src={mascot} alt={`Mascota de ${data.academy.name}`} className="mx-auto w-48 rounded-card sm:w-56" />}
      </section>

      <section>
        <SectionTitle title="Continúa aprendiendo" action={<Link to={`/a/${branding.slug}/rutas`}>Ver todas las rutas</Link>} />
        {data.routes.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sortForLearning(data.routes).map((route, index) => (
              <RouteTile key={route.id} slug={branding.slug} route={route} index={index} />
            ))}
          </div>
        ) : (
          <EmptyState title="Aún no hay clases publicadas" description="Tu admin está preparando el contenido de este club." mascotUrl={mascot} />
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-6">
          <SectionTitle title="Recursos recientes" action={<Link to={`/a/${branding.slug}/recursos`}>Ver todos</Link>} />
          {data.recent_resources.length ? (
            <ul className="grid gap-3">
              {data.recent_resources.map((resource) => {
                const Icon = resourceIcon[resource.type];
                const href = resource.url ?? resource.file_url ?? "#";
                return (
                  <li key={resource.id}>
                    <a href={href} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 rounded-xl p-2 no-underline hover:bg-line/40">
                      <Icon size={22} weight="bold" className="shrink-0 text-secondary" aria-hidden />
                      <span className="font-medium text-ink">{resource.title}</span>
                    </a>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-muted">Sin recursos todavía.</p>
          )}
        </Card>
        <Card className="p-6">
          <SectionTitle title={`#${branding.slug}`} action={<Link to={`/comunidad?canal=${branding.slug}`}>Abrir canal</Link>} />
          {data.latest_posts.length ? (
            <ul className="grid gap-4">
              {data.latest_posts.map((post) => (
                <PostPreview key={post.id} post={post} />
              ))}
            </ul>
          ) : (
            <p className="text-muted">Nadie ha publicado aún.</p>
          )}
        </Card>
        <Card className="p-6">
          <SectionTitle title="Próximos eventos" action={<Link to={`/a/${branding.slug}/eventos`}>Ver eventos</Link>} />
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
      </div>

      <p className="text-center">
        <Link to="/clubes" className="inline-flex items-center gap-1 font-semibold">
          Explorar otros clubes <ArrowRight weight="bold" aria-hidden />
        </Link>
      </p>
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
      { index: true, element: <AcademyHome /> },
      { path: "rutas", element: <RoutesCatalog /> },
    ],
  },
];
