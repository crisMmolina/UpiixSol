import { ArrowRight, Brain, ChartLineUp, Code, Cpu, GraduationCap, Robot, type Icon } from "@phosphor-icons/react";
import { createElement } from "react";
import { Link } from "react-router";

import { Badge } from "@/components/Badge";
import type { RouteCardOut } from "@/lib/types";

// A cover icon picked from the route title (no cover field needed); falls back to a cap.
const ICONS: [RegExp, Icon][] = [
  [/python|c[oó]digo|program/i, Code],
  [/machine|aprendizaje autom|ml\b|red(es)? neuronal|deep/i, Brain],
  [/rob[oó]t/i, Robot],
  [/dato|estad|an[aá]lisis/i, ChartLineUp],
  [/electr|hardware|arduino|embebid/i, Cpu],
];

function coverIcon(title: string): Icon {
  return ICONS.find(([pattern]) => pattern.test(title))?.[1] ?? GraduationCap;
}

export function routeAction(route: RouteCardOut): string {
  const progress = route.progress;
  if (!progress || progress.completed === 0) return "Iniciar ruta";
  return progress.percent === 100 ? "Repasar" : "Continuar";
}

/** Course-catalog card: colored cover tile with the club color, title, progress line, action pill. */
export function RouteCard({ route, slug }: { route: RouteCardOut; slug: string }) {
  const percent = route.progress?.percent ?? 0;
  return (
    <Link to={`/a/${slug}/rutas/${route.id}`} className="group block no-underline" aria-label={`${routeAction(route)}: ${route.title}`}>
      <div className="relative aspect-[16/9] overflow-hidden rounded-card bg-primary text-on-primary transition duration-300 ease-out group-hover:-translate-y-0.5 group-hover:shadow-lift">
        <div aria-hidden className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgb(255_255_255/0.28),transparent_55%)]" />
        <div aria-hidden className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/15 to-transparent" />
        <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-[#16181D]/80 px-2.5 py-1 text-xs font-semibold text-white">
          <GraduationCap size={14} weight="bold" aria-hidden /> Ruta
        </span>
        {!route.is_published && (
          <span className="absolute right-3 top-3">
            <Badge tone="alert">Borrador</Badge>
          </span>
        )}
        {createElement(coverIcon(route.title), {
          "aria-hidden": true,
          size: 72,
          weight: "duotone",
          className: "absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 transition duration-300 group-hover:scale-105",
        })}
        <span className="absolute bottom-3 right-3 inline-flex min-h-10 items-center gap-1.5 rounded-full bg-white px-4 text-sm font-semibold text-[#16181D] shadow-soft">
          {routeAction(route)} <ArrowRight size={16} weight="bold" aria-hidden />
        </span>
      </div>
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-line" aria-hidden>
        <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
      <h2 className="mt-3 text-lg leading-snug text-ink">{route.title}</h2>
      <p className="mt-0.5 text-sm text-muted">
        {route.progress ? `${route.progress.completed} de ${route.progress.total} clases · ${percent} %` : route.description}
      </p>
    </Link>
  );
}
