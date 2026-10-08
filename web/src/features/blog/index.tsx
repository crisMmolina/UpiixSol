// UPS-017: blog.
//   /blog         → published posts, newest first; superadmins also see drafts and create posts
//   /blog/:slug   → post; superadmins edit, upload the cover and delete
import { ArrowLeft, PencilSimple, Plus, Trash } from "@phosphor-icons/react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams, type RouteObject } from "react-router";

import { Avatar } from "@/components/Avatar";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextArea, TextField, fieldErrors } from "@/components/Field";
import { Markdown } from "@/components/Markdown";
import { Modal } from "@/components/Overlay";
import { PageSkeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { slugify } from "@/features/gallery/slug";
import { CampusLayout } from "@/layouts";
import { api, ApiError, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { BlogPostIn, BlogPostOut, Page } from "@/lib/types";

export const order = 61;

const dateFormat = new Intl.DateTimeFormat("es-MX", { dateStyle: "long" });

function excerpt(markdown: string, max = 220): string {
  const text = markdown.replace(/[#*_>`[\]()!-]/g, " ").replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max).trimEnd()}…` : text;
}

function Byline({ post }: { post: BlogPostOut }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted">
      {post.author && <Avatar user={post.author} size="sm" />}
      <p className="min-w-0">
        <span className="font-semibold text-ink">{post.author?.nickname}</span>
        {post.published_at && <> · {dateFormat.format(new Date(post.published_at))}</>}
      </p>
      {!post.published_at && <Badge tone="alert">Borrador</Badge>}
    </div>
  );
}

function BlogPage() {
  const isSuper = useAuth().user?.role === "superadmin";
  const [params, setParams] = useSearchParams();
  const drafts = isSuper && params.get("borradores") === "1";
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

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="mb-2 text-3xl sm:text-4xl">Blog</h1>
          <p className="text-muted">Noticias y avisos de la mesa directiva.</p>
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
        <PageSkeleton />
      ) : items.length === 0 ? (
        <EmptyState title="Aún no hay entradas" description="Vuelve pronto para ver las novedades del club." />
      ) : (
        <>
          <ul className="grid gap-5">
            {items.map((post) => (
              <li key={post.id}>
                <Link to={`/blog/${post.slug}`} className="no-underline">
                  <Card
                    interactive
                    // The image column exists only when there is an image; otherwise the text gets the full width.
                    className={`grid gap-4 p-5 ${post.cover_url?.startsWith("/media/") ? "sm:grid-cols-[16rem_1fr] sm:items-center" : ""}`}
                  >
                    {post.cover_url?.startsWith("/media/") && (
                      <img src={post.cover_url} alt="" loading="lazy" className="aspect-[16/10] w-full rounded-2xl bg-bg object-cover" />
                    )}
                    <div className="grid max-w-prose content-start gap-2">
                      <h2 className="text-2xl text-balance">{post.title}</h2>
                      <Byline post={post} />
                      <p className="text-muted">{excerpt(post.body)}</p>
                    </div>
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
