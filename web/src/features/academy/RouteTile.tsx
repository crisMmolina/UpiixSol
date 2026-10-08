// Route cover tile shared by the club home and the route catalog: club color + icon, title,
// progress line and the "Iniciar / Continuar / Repasar" pill on the cover.
import { BookOpenText, Code, Compass, Lightbulb, Rocket, Sparkle, Target, type Icon } from "@phosphor-icons/react";
import { Link } from "react-router";

import { Badge } from "@/components/Badge";
import { ProgressBar } from "@/components/ProgressBar";
import { Skeleton } from "@/components/Skeleton";
import { api } from "@/lib/api";
import type { RouteCardOut } from "@/lib/types";

const icons: Icon[] = [Rocket, Compass, Lightbulb, Code, Target, Sparkle, BookOpenText];

export type RouteStatus = "Iniciar" | "Continuar" | "Repasar";

export function routeStatus(route: RouteCardOut): RouteStatus {
  const progress = route.progress;
  if (!progress || progress.completed === 0) return "Iniciar";
  return progress.percent >= 100 ? "Repasar" : "Continuar";
}

const enrollRequested = new Set<string>();

/** Membership is implicit now: opening a route enrolls the member quietly (idempotent on the API). */
export function ensureEnrolled(slug: string) {
  if (enrollRequested.has(slug)) return;
  enrollRequested.add(slug);
  api(`/academies/${slug}/enroll`, { method: "POST" }).catch(() => enrollRequested.delete(slug));
}

export function RouteTile({ slug, route, index }: { slug: string; route: RouteCardOut; index: number }) {
  const Glyph = icons[index % icons.length];
  const status = routeStatus(route);
  const progress = route.progress;
  return (
    <Link
      to={`/a/${slug}/rutas/${route.id}`}
      onClick={() => ensureEnrolled(slug)}
      className="group block h-full rounded-card no-underline"
      aria-label={`${status}: ${route.title}`}
    >
      <article className="flex h-full flex-col overflow-hidden rounded-card border border-line bg-surface shadow-soft transition duration-200 group-hover:-translate-y-0.5 group-hover:shadow-lift motion-reduce:transition-none motion-reduce:group-hover:translate-y-0">
        <div className="relative isolate flex aspect-[16/9] items-center justify-center overflow-hidden bg-primary text-on-primary">
          <span aria-hidden className="absolute -right-8 -top-10 -z-10 size-40 rounded-full bg-white/20" />
          <span aria-hidden className="absolute -bottom-12 -left-6 -z-10 size-36 rounded-full bg-black/10" />
          <Glyph size={64} weight="duotone" aria-hidden />
          <span className="absolute bottom-3 right-3 inline-flex min-h-8 items-center rounded-full bg-white px-4 text-sm font-semibold text-ink shadow-soft">
            {status}
          </span>
          {!route.is_published && (
            <span className="absolute left-3 top-3">
              <Badge tone="alert">Borrador</Badge>
            </span>
          )}
        </div>
        <div className="grid flex-1 content-start gap-2 p-4">
          <h3 className="text-lg leading-snug">{route.title}</h3>
          {progress && (
            <>
              <ProgressBar percent={progress.percent} label={`Progreso de ${route.title}`} size="sm" />
              <p className="text-xs text-muted">
                {progress.completed} de {progress.total} clases
              </p>
            </>
          )}
        </div>
      </article>
    </Link>
  );
}

export function RouteTileSkeleton() {
  return (
    <div aria-hidden className="overflow-hidden rounded-card border border-line bg-surface shadow-soft">
      <Skeleton className="aspect-[16/9] w-full rounded-none" />
      <div className="grid gap-2 p-4">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-3 w-1/3" />
      </div>
    </div>
  );
}

export function RouteGridSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div role="status" aria-label="Cargando rutas" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }, (_, i) => (
        <RouteTileSkeleton key={i} />
      ))}
    </div>
  );
}
