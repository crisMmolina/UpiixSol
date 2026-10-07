// Flow step 2 (UPS-006): academy home — re-themed campus, "Continuar donde te quedaste", routes, resources,
// latest posts of its channel and upcoming events.
import { ArrowRight, BookOpenText, FileText, LinkSimple, PlayCircle, Plus, VideoCamera } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { Link, type RouteObject } from "react-router";

import { Button, ButtonLink } from "@/components/Button";
import { Card, SectionTitle } from "@/components/Card";
import { Markdown } from "@/components/Markdown";
import { ProgressBar } from "@/components/ProgressBar";
import { PageSkeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import { RequireRole } from "@/lib/auth";
import { safeAssetPath } from "@/lib/theme";
import type { AcademyOut, ContinueOut, EventOut, PostOut, ResourceOut, ResourceType, RouteCardOut } from "@/lib/types";
import { AcademyLayout, useAcademy } from "@/layouts";

import { EventItem, PostPreview } from "../home";

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

const resourceIcon: Record<ResourceType, typeof FileText> = {
  document: FileText,
  link: LinkSimple,
  video: VideoCamera,
  other: BookOpenText,
};

function ContinueCard({ slug, info }: { slug: string; info: ContinueOut }) {
  const done = info.percent === 100;
  return (
    <Card stripe className="grid gap-4 p-6 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p className="text-sm font-semibold text-link">{done ? "¡Ruta completada!" : "Continuar donde te quedaste"}</p>
        <h2 className="mt-1 text-2xl">
          Clase {info.lesson_number} · {info.lesson_title}
        </h2>
        <div className="mt-3 max-w-md">
          <ProgressBar percent={info.percent} label="Progreso de la ruta" />
        </div>
      </div>
      <ButtonLink to={`/a/${slug}/clases/${info.lesson_id}`} size="lg" icon={<PlayCircle weight="fill" />}>
        {done ? "Repasar" : `Continuar: Clase ${info.lesson_number} · ${info.percent} %`}
      </ButtonLink>
    </Card>
  );
}

function AcademyHome() {
  const branding = useAcademy();
  const [data, setData] = useState<AcademyHomeOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);

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

  async function enroll() {
    setEnrolling(true);
    try {
      await api(`/academies/${branding.slug}/enroll`, { method: "POST" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setEnrolling(false);
    }
  }

  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!data) return <PageSkeleton />;

  const mascot = safeAssetPath(branding.mascot_url);
  return (
    <div className="grid gap-8">
      <section className="grid items-center gap-6 rounded-card border border-line bg-surface p-6 shadow-soft sm:p-8 md:grid-cols-[1fr_auto]">
        <div>
          <p className="text-sm font-semibold text-link">Bienvenida a la academia</p>
          <h1 className="mt-1 text-3xl sm:text-4xl">{data.academy.name}</h1>
          {data.academy.welcome_text && <Markdown source={data.academy.welcome_text} className="mt-3 max-w-2xl text-lg" />}
          {!data.is_enrolled && (
            <Button className="mt-5" onClick={enroll} loading={enrolling} icon={<Plus weight="bold" />}>
              Inscribirme a {data.academy.name}
            </Button>
          )}
        </div>
        {mascot && <img src={mascot} alt={`Mascota de ${data.academy.name}`} className="mx-auto w-48 rounded-card sm:w-56" />}
      </section>

      {data.continue ? (
        <ContinueCard slug={branding.slug} info={data.continue} />
      ) : (
        <EmptyState title="Aún no hay clases publicadas" description="Tu admin está preparando el contenido de esta academia." mascotUrl={mascot} />
      )}

      {data.routes.length > 0 && (
        <section>
          <SectionTitle title="Mis rutas de aprendizaje" action={<Link to={`/a/${branding.slug}/rutas`}>Ver todas</Link>} />
          <div className="grid gap-4 md:grid-cols-2">
            {data.routes.map((route) => (
              <Link key={route.id} to={`/a/${branding.slug}/rutas/${route.id}`} className="no-underline">
                <Card interactive className="grid h-full gap-3 p-5">
                  <h3 className="text-xl">{route.title}</h3>
                  {route.description && <p className="text-sm text-muted">{route.description}</p>}
                  {route.progress && (
                    <>
                      <ProgressBar percent={route.progress.percent} label={`Progreso de ${route.title}`} />
                      <p className="text-xs text-muted">
                        {route.progress.completed} de {route.progress.total} clases completadas
                      </p>
                    </>
                  )}
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

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
        <Link to="/academias" className="inline-flex items-center gap-1 font-semibold">
          Explorar otras academias <ArrowRight weight="bold" aria-hidden />
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
    children: [{ index: true, element: <AcademyHome /> }],
  },
];
