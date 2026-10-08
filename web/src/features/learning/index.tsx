// Flow step 3 (UPS-007, redesign UPS-024): learning routes and the course player.
//   /a/:slug/rutas                 → route catalog of the club
//   /a/:slug/rutas/:routeId        → resume the route (next unfinished lesson)
//   /a/:slug/clases/:lessonId      → dark course player (Player.tsx)
import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { Navigate, useParams, type RouteObject } from "react-router";

import { GridSkeleton, PageSkeleton, Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import { RequireRole } from "@/lib/auth";
import type { Page, RouteCardOut, RouteDetailOut } from "@/lib/types";
import { AcademyLayout, useAcademy } from "@/layouts";

import { CoursePage } from "./Player";
import { RouteCard } from "./RouteCard";

export const order = 40;

// ── Route catalog ────────────────────────────────────────────

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

  return (
    <div>
      <h1 className="text-3xl sm:text-4xl">Rutas</h1>
      <p className="mb-8 mt-1 text-muted">Cada ruta tiene módulos y clases en video. Tu avance se guarda solo.</p>
      {error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : !routes ? (
        <GridSkeleton count={4} className="xl:grid-cols-3" />
      ) : routes.length === 0 ? (
        <EmptyState title="Aún no hay rutas publicadas" mascotUrl={academy.mascot_url} />
      ) : (
        <div className="grid gap-x-6 gap-y-10 sm:grid-cols-2 xl:grid-cols-3">
          {routes.map((route, index) => (
            <div key={route.id} className="enter" style={{ "--i": index } as CSSProperties}>
              <RouteCard route={route} slug={academy.slug} />
            </div>
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
  if (target === undefined) return <Skeleton className="aspect-video w-full rounded-2xl" />;
  if (target === null) return <EmptyState title="Esta ruta aún no tiene clases" mascotUrl={academy.mascot_url} />;
  return <Navigate to={`/a/${academy.slug}/clases/${target}`} replace />;
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
    ],
  },
  {
    // Immersive dark course view: outside the app shell, with its own top bar.
    path: "/a/:slug/clases/:lessonId",
    element: (
      <RequireRole>
        <CoursePage />
      </RequireRole>
    ),
  },
];

export { RouteCard } from "./RouteCard";
export { PageSkeleton };
