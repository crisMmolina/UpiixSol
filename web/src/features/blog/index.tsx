// UPS-017: blog.
//   /blog         → published posts, newest first; superadmins also see drafts and create posts
//   /blog/:slug   → post; superadmins edit, upload the cover and delete
import { ArrowLeft, MagnifyingGlass, Newspaper, PencilSimple, Plus, Trash } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams, type RouteObject } from "react-router";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextArea, TextField, fieldErrors } from "@/components/Field";
import { Markdown } from "@/components/Markdown";
import { Modal } from "@/components/Overlay";
import { PageSkeleton, Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { slugify } from "@/features/gallery/slug";
import { CampusLayout } from "@/layouts";
import { api, ApiError, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { BlogPostIn, BlogPostOut, Page } from "@/lib/types";

export const order = 61;

const dateFormat = new Intl.DateTimeFormat("es-MX", { dateStyle: "long" });

const WORDS_PER_MINUTE = 200;

/** Reading time from the body length (about 200 words per minute, at least 1 minute). */
function readMinutes(markdown: string): number {
  const words = markdown.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / WORDS_PER_MINUTE));
}

function excerpt(markdown: string, max = 160): string {
  const text = markdown.replace(/[#*_>`[\]()!-]/g, " ").replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max).trimEnd()}…` : text;
}

const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

function Byline({ post }: { post: BlogPostOut }) {
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted">
      {post.author && <Avatar user={post.author} size="sm" />}
      <p className="min-w-0">
        <span className="font-semibold text-ink">{post.author?.nickname}</span>
        {post.published_at && <> · {dateFormat.format(new Date(post.published_at))}</>}
        <> · {readMinutes(post.body)} min de lectura</>
      </p>
      {!post.published_at && <Badge tone="alert">Borrador</Badge>}
    </div>
  );
}

function Cover({ post, className = "" }: { post: BlogPostOut; className?: string }) {
  if (post.cover_url?.startsWith("/media/")) {
    return <img src={post.cover_url} alt="" loading="lazy" className={`w-full rounded-2xl bg-bg object-cover ${className}`} />;
  }
  return (
    <div aria-hidden className={`grid w-full place-items-center rounded-2xl bg-primary/10 text-secondary ${className}`}>
      <Newspaper size={40} />
    </div>
  );
}

function BlogSkeleton() {
  return (
    <div role="status" aria-label="Cargando" className="grid gap-6">
      <Card className="grid gap-4 p-5 lg:grid-cols-[1.2fr_1fr]">
        <Skeleton className="aspect-[16/9] w-full" />
        <div className="grid content-center gap-3">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </Card>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Card key={i} className="grid gap-3 p-4">
            <Skeleton className="aspect-[16/9] w-full" />
            <Skeleton className="h-6 w-5/6" />
            <Skeleton className="h-4 w-full" />
          </Card>
        ))}
      </div>
    </div>
  );
}

function BlogPage() {
  const isSuper = useAuth().user?.role === "superadmin";
  const [params, setParams] = useSearchParams();
  const drafts = isSuper && params.get("borradores") === "1";
  const author = params.get("autor");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<BlogPostOut[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const fetchPage = useCallback(
    (after: string | null) => api<Page<BlogPostOut>>("/blog", { query: { drafts: drafts || undefined, cursor: after } }),
    [drafts],
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

  // The API has no categories or search: chips are the authors of the loaded posts, and the search
  // runs in the browser over the posts already loaded (title, body and author).
  const authors = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of items ?? []) if (p.author) counts.set(p.author.nickname, (counts.get(p.author.nickname) ?? 0) + 1);
    return [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([nick]) => nick);
  }, [items]);

  const term = normalize(query.trim());
  const filtering = Boolean(term || author);
  const visible = useMemo(
    () =>
      (items ?? []).filter(
        (p) =>
          (!author || p.author?.nickname === author) &&
          (!term || normalize(`${p.title} ${p.body} ${p.author?.nickname ?? ""}`).includes(term)),
      ),
    [items, author, term],
  );
  const [featured, ...rest] = visible;
  // "Trending" = the most recent posts after the featured one. There are no view or like counts.
  const trending = filtering ? [] : rest.slice(0, 3);
  const grid = filtering ? rest : rest.slice(3);

  function pickAuthor(nick: string | null) {
    const next = new URLSearchParams(params);
    if (nick) next.set("autor", nick);
    else next.delete("autor");
    setParams(next);
  }

  return (
    <div className="grid gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-2 text-3xl sm:text-4xl">Blog</h1>
          <p className="max-w-xl text-muted">Noticias, guías y avisos de la mesa directiva y de los clubs.</p>
        </div>
        {isSuper && (
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setParams(drafts ? {} : { borradores: "1" })}>
              {drafts ? "Ver publicadas" : "Ver borradores"}
            </Button>
            <Button icon={<Plus weight="bold" />} onClick={() => setCreating(true)}>
              Nueva entrada
            </Button>
          </div>
        )}
      </div>

      {error ? (
        <ErrorState message={error} />
      ) : items === null ? (
        <BlogSkeleton />
      ) : items.length === 0 ? (
        <EmptyState title="Aún no hay entradas" description="Vuelve pronto para ver las novedades del club." />
      ) : (
        <>
          <div className="grid gap-3">
            <label className="relative block max-w-xl">
              <span className="sr-only">Buscar en el blog</span>
              <MagnifyingGlass aria-hidden className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted" size={20} />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar artículos"
                className="min-h-11 w-full rounded-full border border-line bg-surface pl-11 pr-4 text-ink placeholder:text-muted focus-visible:outline-2 focus-visible:outline-offset-2"
              />
            </label>
            {authors.length > 1 && (
              <nav aria-label="Filtrar por autor" className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
                {[null, ...authors].map((nick) => (
                  <button
                    key={nick ?? "todos"}
                    type="button"
                    aria-pressed={author === nick}
                    onClick={() => pickAuthor(nick)}
                    className={`min-h-11 shrink-0 rounded-full border px-4 text-sm font-semibold transition ${
                      author === nick ? "border-primary/40 bg-primary/15 text-ink" : "border-line bg-surface text-ink hover:border-secondary"
                    }`}
                  >
                    {nick ?? "Todos"}
                  </button>
                ))}
              </nav>
            )}
          </div>

          {!featured ? (
            <EmptyState
              title="No encontramos artículos"
              description="Prueba con otras palabras o quita los filtros."
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setQuery("");
                    pickAuthor(null);
                  }}
                >
                  Limpiar búsqueda
                </Button>
              }
            />
          ) : (
            <>
              <Link to={`/blog/${featured.slug}`} className="no-underline">
                <Card interactive className="grid gap-5 p-4 sm:p-5 lg:grid-cols-[1.2fr_1fr] lg:items-center">
                  <Cover post={featured} className="aspect-[16/9]" />
                  <div className="grid content-center gap-3">
                    <Badge>Destacado</Badge>
                    <h2 className="text-2xl text-balance sm:text-3xl">{featured.title}</h2>
                    <p className="text-muted">{excerpt(featured.body, 220)}</p>
                    <Byline post={featured} />
                  </div>
                </Card>
              </Link>

              {trending.length > 0 && (
                <section aria-labelledby="trending" className="grid gap-3">
                  <div>
                    <h2 id="trending" className="text-xl">
                      Artículos en tendencia
                    </h2>
                    <p className="text-sm text-muted">Los más recientes del blog.</p>
                  </div>
                  <ol className="grid gap-3 md:grid-cols-3">
                    {trending.map((post, i) => (
                      <li key={post.id}>
                        <Link to={`/blog/${post.slug}`} className="no-underline">
                          <Card interactive className="flex h-full items-start gap-3 p-4">
                            <span aria-hidden className="text-3xl font-bold text-secondary/60">
                              {i + 1}
                            </span>
                            <div className="grid gap-1">
                              <h3 className="text-base text-balance">{post.title}</h3>
                              <p className="text-sm text-muted">{readMinutes(post.body)} min de lectura</p>
                            </div>
                          </Card>
                        </Link>
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              {grid.length > 0 && (
                <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {grid.map((post) => (
                    <li key={post.id}>
                      <Link to={`/blog/${post.slug}`} className="no-underline">
                        <Card interactive className="flex h-full flex-col gap-3 p-4">
                          <Cover post={post} className="hidden aspect-[16/9] sm:grid" />
                          <h2 className="text-xl text-balance">{post.title}</h2>
                          <p className="text-sm text-muted">{excerpt(post.body)}</p>
                          <div className="mt-auto pt-1">
                            <Byline post={post} />
                          </div>
                        </Card>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
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
        <Modal open onClose={() => setCreating(false)} title="Nueva entrada">
          <PostForm onClose={() => setCreating(false)} onSaved={(p) => navigate(`/blog/${p.slug}`)} />
        </Modal>
      )}
    </div>
  );
}

function PostPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const isSuper = useAuth().user?.role === "superadmin";
  const navigate = useNavigate();
  const [post, setPost] = useState<BlogPostOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    let alive = true;
    api<BlogPostOut>(`/blog/${encodeURIComponent(slug)}`)
      .then((p) => alive && setPost(p))
      .catch((err) => alive && setError(err));
    return () => {
      alive = false;
    };
  }, [slug]);

  async function remove() {
    if (!post || !window.confirm(`¿Eliminar "${post.title}"? No se puede deshacer.`)) return;
    try {
      await api(`/blog/${post.id}`, { method: "DELETE" });
      navigate("/blog");
    } catch (err) {
      setError(err);
    }
  }

  if (error) {
    return error instanceof ApiError && error.status === 404 ? (
      <EmptyState title="Esta entrada no existe o aún no se publica" action={<Link to="/blog">Ver el blog</Link>} />
    ) : (
      <ErrorState message={errorMessage(error)} />
    );
  }
  if (!post) return <PageSkeleton />;

  return (
    <article className="mx-auto grid max-w-3xl gap-5">
      <Link to="/blog" className="inline-flex min-h-11 items-center gap-1 font-semibold">
        <ArrowLeft weight="bold" aria-hidden /> Blog
      </Link>
      {post.cover_url?.startsWith("/media/") && (
        <img src={post.cover_url} alt={`Portada de ${post.title}`} className="aspect-[16/9] w-full rounded-2xl bg-bg object-cover" />
      )}
      <h1 className="text-3xl sm:text-4xl">{post.title}</h1>
      <Byline post={post} />
      <Markdown source={post.body} />
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
        <Modal open onClose={() => setEditing(false)} title="Editar entrada">
          <PostForm
            post={post}
            onClose={() => setEditing(false)}
            onSaved={(p) => (p.slug === slug ? setPost(p) : navigate(`/blog/${p.slug}`, { replace: true }))}
          />
        </Modal>
      )}
    </article>
  );
}

function PostForm({ post, onClose, onSaved }: { post?: BlogPostOut; onClose: () => void; onSaved: (p: BlogPostOut) => void }) {
  const [slug, setSlug] = useState(post?.slug ?? "");
  const [slugTouched, setSlugTouched] = useState(Boolean(post));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const cover = form.get("cover");
    const payload: BlogPostIn = {
      title: String(form.get("title")).trim(),
      slug: slug.trim(),
      body: String(form.get("body")),
      published: form.get("published") === "on",
    };
    setBusy(true);
    setError(null);
    setErrors({});
    try {
      let saved = post
        ? await api<BlogPostOut>(`/blog/${post.id}`, { method: "PUT", json: payload })
        : await api<BlogPostOut>("/blog", { method: "POST", json: payload });
      if (cover instanceof File && cover.size > 0) {
        const upload = new FormData();
        upload.append("file", cover);
        saved = await api<BlogPostOut>(`/blog/${saved.id}/cover`, { method: "POST", form: upload });
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
        defaultValue={post?.title}
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
      <TextArea label="Contenido (markdown)" name="body" defaultValue={post?.body} rows={10} error={errors.body} />
      <TextField label={post?.cover_url ? "Reemplazar portada" : "Portada (opcional)"} name="cover" type="file" accept="image/png,image/jpeg,image/webp" hint="PNG, JPG o WebP de hasta 5 MB." />
      <label className="flex min-h-11 items-center gap-2 text-sm font-semibold">
        <input type="checkbox" name="published" defaultChecked={Boolean(post?.published_at)} className="size-4" />
        Publicada (visible para todos)
      </label>
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
          {post ? "Guardar cambios" : "Crear entrada"}
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
      { path: "/blog", element: <BlogPage /> },
      { path: "/blog/:slug", element: <PostPage /> },
    ],
  },
];
