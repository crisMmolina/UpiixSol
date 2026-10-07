// UPS-017: project gallery.
//   /galeria         → published projects (blog-style cards, tag filter); superadmins also see drafts
//   /galeria/:slug   → detail; superadmins create, edit, upload the cover and delete
import { ArrowLeft, Cube, PencilSimple, Plus, Trash, X } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams, type RouteObject } from "react-router";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { SelectField, TextArea, TextField, fieldErrors } from "@/components/Field";
import { Markdown } from "@/components/Markdown";
import { Modal } from "@/components/Overlay";
import { PageSkeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { CampusLayout } from "@/layouts";
import { api, ApiError, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { Page, ProjectIn, ProjectOut } from "@/lib/types";

import { slugify } from "./slug";

export const order = 60;

const dateFormat = new Intl.DateTimeFormat("es-MX", { dateStyle: "long" });

const byline = (project: ProjectOut) =>
  [project.authors, project.published_at && dateFormat.format(new Date(project.published_at))].filter(Boolean).join(" · ");

function useIsSuperadmin(): boolean {
  return useAuth().user?.role === "superadmin";
}

function Cover({ url, title }: { url: string | null; title: string }) {
  if (!url?.startsWith("/media/")) return null;
  return <img src={url} alt={`Portada de ${title}`} loading="lazy" className="aspect-[16/9] w-full rounded-2xl bg-bg object-cover" />;
}

// In the multi-column grid, cards keep one shape with or without a cover so rows stay aligned;
// on a phone (one column) the placeholder would only push content down, so it is hidden.
function CardCover({ project }: { project: ProjectOut }) {
  if (project.cover_url?.startsWith("/media/")) return <Cover url={project.cover_url} title={project.title} />;
  return (
    <div aria-hidden className="hidden aspect-[16/9] w-full place-items-center rounded-2xl bg-primary/10 text-secondary sm:grid">
      <Cube size={40} />
    </div>
  );
}

// The summary leads the detail page only when the body does not already open with it.
const leadSummary = (project: ProjectOut) =>
  project.summary && !project.body.trimStart().startsWith(project.summary.trim()) ? project.summary : null;

// ── Listing ──────────────────────────────────────────────────

function GalleryPage() {
  const isSuper = useIsSuperadmin();
  const [params, setParams] = useSearchParams();
  const tag = params.get("tag");
  const drafts = isSuper && params.get("borradores") === "1";
  const [items, setItems] = useState<ProjectOut[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  // Filter chips come from the projects already on screen, most used first.
  const tags = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of items ?? []) for (const t of p.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
    return [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([t]) => t);
  }, [items]);

  const fetchPage = useCallback(
    (after: string | null) => api<Page<ProjectOut>>("/projects", { query: { tag, drafts: drafts || undefined, cursor: after } }),
    [tag, drafts],
  );

  useEffect(() => {
    let alive = true;
    fetchPage(null)
      .then((page) => {
        if (!alive) return;
        setItems(page.items);
        setCursor(page.next_cursor ?? null);
        setError(null);
      })
      .catch((err) => alive && setError(errorMessage(err)));
    return () => {
      alive = false;
    };
  }, [fetchPage]);

  async function loadMore() {
    try {
      const page = await fetchPage(cursor);
      setItems((prev) => [...(prev ?? []), ...page.items]);
      setCursor(page.next_cursor ?? null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-2 text-3xl sm:text-4xl">Galería de proyectos</h1>
          <p className="text-muted">Lo que construyen las academias del club.</p>
        </div>
        {isSuper && (
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setParams(drafts ? {} : { borradores: "1" })}>
              {drafts ? "Ver publicados" : "Ver borradores"}
            </Button>
            <Button icon={<Plus weight="bold" />} onClick={() => setCreating(true)}>
              Nuevo proyecto
            </Button>
          </div>
        )}
      </div>

      {tag ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted">Proyectos con la etiqueta</span>
          <button
            type="button"
            onClick={() => setParams(drafts ? { borradores: "1" } : {})}
            className="inline-flex min-h-11 items-center gap-1.5 rounded-full border border-primary/40 bg-primary/15 px-4 font-semibold text-ink"
          >
            #{tag}
            <X weight="bold" aria-hidden />
            <span className="sr-only">Quitar filtro</span>
          </button>
        </div>
      ) : (
        tags.length > 0 && (
          <nav aria-label="Filtrar por etiqueta" className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
            {tags.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setParams(drafts ? { borradores: "1", tag: t } : { tag: t })}
                className="min-h-11 shrink-0 rounded-full border border-line bg-surface px-4 text-sm font-semibold text-ink transition hover:border-secondary"
              >
                #{t}
              </button>
            ))}
          </nav>
        )
      )}

      {error ? (
        <ErrorState message={error} />
      ) : items === null ? (
        <PageSkeleton />
      ) : items.length === 0 ? (
        <EmptyState title="Aún no hay proyectos publicados" description="Pronto verás aquí lo que construye el club." />
      ) : (
        <>
          <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((project) => (
              <li key={project.id}>
                <Link to={`/galeria/${project.slug}`} className="no-underline">
                  <Card interactive className="flex h-full flex-col gap-3 p-4">
                    <CardCover project={project} />
                    <div className="flex items-start justify-between gap-2">
                      <h2 className="text-xl">{project.title}</h2>
                      {project.status === "draft" && <Badge tone="alert">Borrador</Badge>}
                    </div>
                    {project.summary && <p className="text-sm text-muted">{project.summary}</p>}
                    {project.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {project.tags.slice(0, 3).map((t) => (
                          <Badge key={t}>#{t}</Badge>
                        ))}
                      </div>
                    )}
                    <p className="mt-auto pt-1 text-sm text-muted">{byline(project)}</p>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
          {cursor && (
            <div className="text-center">
              <Button variant="secondary" onClick={() => void loadMore()}>
                Cargar más
              </Button>
            </div>
          )}
        </>
      )}

      {creating && (
        <Modal open onClose={() => setCreating(false)} title="Nuevo proyecto">
          <ProjectForm onClose={() => setCreating(false)} onSaved={(p) => navigate(`/galeria/${p.slug}`)} />
        </Modal>
      )}
    </div>
  );
}

// ── Detail ───────────────────────────────────────────────────

function ProjectPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const isSuper = useIsSuperadmin();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectOut | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    let alive = true;
    api<ProjectOut>(`/projects/${encodeURIComponent(slug)}`)
      .then((p) => alive && setProject(p))
      .catch((err) => alive && setError(err));
    return () => {
      alive = false;
    };
  }, [slug]);

  async function remove() {
    if (!project || !window.confirm(`¿Eliminar "${project.title}"? No se puede deshacer.`)) return;
    try {
      await api(`/projects/${project.id}`, { method: "DELETE" });
      navigate("/galeria");
    } catch (err) {
      setError(err as Error);
    }
  }

  if (error) {
    return error instanceof ApiError && error.status === 404 ? (
      <EmptyState title="Este proyecto no existe o aún no se publica" action={<Link to="/galeria">Ver la galería</Link>} />
    ) : (
      <ErrorState message={errorMessage(error)} />
    );
  }
  if (!project) return <PageSkeleton />;

  return (
    <article className="mx-auto grid max-w-3xl gap-5">
      <Link to="/galeria" className="inline-flex min-h-11 items-center gap-1 font-semibold">
        <ArrowLeft weight="bold" aria-hidden /> Galería
      </Link>
      <Cover url={project.cover_url} title={project.title} />
      <header className="grid gap-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-3xl sm:text-4xl">{project.title}</h1>
          {project.status === "draft" && <Badge tone="alert">Borrador</Badge>}
        </div>
        <p className="text-muted">
          {byline(project)}
        </p>
        {project.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {project.tags.map((tag) => (
              <Link
                key={tag}
                to={`/galeria?tag=${encodeURIComponent(tag)}`}
                className="inline-flex min-h-11 items-center rounded-full border border-line bg-surface px-4 text-sm font-semibold text-ink no-underline transition hover:border-secondary"
              >
                #{tag}
              </Link>
            ))}
          </div>
        )}
      </header>
      {leadSummary(project) && <p className="text-lg">{leadSummary(project)}</p>}
      <Markdown source={project.body} />
      {isSuper && (
        <div className="flex flex-wrap gap-2 border-t border-line pt-4">
          <Button variant="secondary" icon={<PencilSimple weight="bold" />} onClick={() => setEditing(true)}>
            Editar
          </Button>
          <Button variant="danger" icon={<Trash weight="bold" />} onClick={() => void remove()}>
            Eliminar
          </Button>
        </div>
      )}
      {editing && (
        <Modal open onClose={() => setEditing(false)} title="Editar proyecto">
          <ProjectForm
            project={project}
            onClose={() => setEditing(false)}
            onSaved={(p) => (p.slug === slug ? setProject(p) : navigate(`/galeria/${p.slug}`, { replace: true }))}
          />
        </Modal>
      )}
    </article>
  );
}

// ── Superadmin form ──────────────────────────────────────────

function ProjectForm({ project, onClose, onSaved }: { project?: ProjectOut; onClose: () => void; onSaved: (p: ProjectOut) => void }) {
  const [slug, setSlug] = useState(project?.slug ?? "");
  const [slugTouched, setSlugTouched] = useState(Boolean(project));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const cover = form.get("cover");
    const payload: ProjectIn = {
      title: String(form.get("title")).trim(),
      slug: slug.trim(),
      summary: String(form.get("summary")).trim(),
      body: String(form.get("body")),
      authors: String(form.get("authors")).trim(),
      tags: String(form.get("tags"))
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      status: form.get("status") === "published" ? "published" : "draft",
      academy_id: project?.academy_id ?? null,
    };
    setBusy(true);
    setError(null);
    setErrors({});
    try {
      let saved = project
        ? await api<ProjectOut>(`/projects/${project.id}`, { method: "PUT", json: payload })
        : await api<ProjectOut>("/projects", { method: "POST", json: payload });
      if (cover instanceof File && cover.size > 0) {
        const upload = new FormData();
        upload.append("file", cover);
        saved = await api<ProjectOut>(`/projects/${saved.id}/cover`, { method: "POST", form: upload });
      }
      onSaved(saved);
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setErrors(fieldErrors(err.details));
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      <TextField
        label="Título"
        name="title"
        defaultValue={project?.title}
        required
        maxLength={120}
        error={errors.title}
        onChange={(e) => !slugTouched && setSlug(slugify(e.target.value))}
      />
      <TextField
        label="Identificador en la URL (slug)"
        name="slug"
        value={slug}
        onChange={(e) => {
          setSlugTouched(true);
          setSlug(e.target.value);
        }}
        hint="Minúsculas, números y guiones."
        error={errors.slug}
      />
      <TextField label="Resumen" name="summary" defaultValue={project?.summary} maxLength={300} error={errors.summary} />
      <TextField label="Autores" name="authors" defaultValue={project?.authors} maxLength={300} />
      <TextField label="Etiquetas (separadas por coma)" name="tags" defaultValue={project?.tags.join(", ")} error={errors.tags} />
      <TextArea label="Descripción (markdown)" name="body" defaultValue={project?.body} rows={6} error={errors.body} />
      <SelectField label="Estado" name="status" defaultValue={project?.status ?? "draft"}>
        <option value="draft">Borrador (solo superadmins)</option>
        <option value="published">Publicado</option>
      </SelectField>
      <TextField label={project?.cover_url ? "Reemplazar portada" : "Portada (opcional)"} name="cover" type="file" accept="image/png,image/jpeg,image/webp" hint="PNG, JPG o WebP de hasta 5 MB." />
      {error && (
        <p role="alert" className="rounded-xl bg-accent-2/10 px-3 py-2 text-sm font-semibold text-accent-2">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" loading={busy}>
          {project ? "Guardar cambios" : "Crear proyecto"}
        </Button>
      </div>
    </form>
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
      { path: "/galeria", element: <GalleryPage /> },
      { path: "/galeria/:slug", element: <ProjectPage /> },
    ],
  },
];
