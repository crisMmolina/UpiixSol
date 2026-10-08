// Flow step 4 (UPS-011, redesign UPS-025): Discord-style community with Feed, General and one channel
// per club. Inside a club (/a/:slug/comunidad) only that club's channel is shown, in the club layout.
// Hidden posts/comments stay in place as "Mensaje oculto". No realtime in v1: refresh every 30 s.
import { ChatCircle, EyeSlash, Hash, ImageSquare, LinkSimple, PaperPlaneRight, Rss } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { Link, useSearchParams, type RouteObject } from "react-router";

import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Markdown } from "@/components/Markdown";
import { ListSkeleton, Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState, Notice } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { AcademyCardOut, ChannelOut, CommentOut, Page, PostOut, UserMe } from "@/lib/types";
import { AcademyLayout, CampusLayout, useAcademy } from "@/layouts";

import { Reactions } from "./Reactions";

export const order = 35;

const REFRESH_MS = 30_000;
const POST_MAX_CHARS = 512; // same limit as the API (app/schemas/community.py)
const relative = new Intl.RelativeTimeFormat("es-MX", { numeric: "auto" });

function timeAgo(iso: string): string {
  const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60_000);
  if (Math.abs(minutes) < 60) return relative.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return relative.format(hours, "hour");
  return relative.format(Math.round(hours / 24), "day");
}

function canModerate(user: UserMe | null, channel: ChannelOut | undefined): boolean {
  if (!user || !channel) return false;
  if (user.role === "superadmin") return true;
  return user.role === "academy_admin" && channel.academy_id !== null && channel.academy_id === user.academy_id;
}

function Composer({ channel, onPosted }: { channel: ChannelOut; onPosted: (post: PostOut) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showLink, setShowLink] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [length, setLength] = useState(0);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    if (!String(form.get("body")).trim()) return setError("Escribe algo antes de publicar.");
    const image = form.get("image") as File | null;
    if (!image || image.size === 0) form.delete("image");
    if (!String(form.get("link_url") ?? "").trim()) form.delete("link_url");
    setBusy(true);
    setError(null);
    try {
      onPosted(await api<PostOut>(`/channels/${channel.id}/posts`, { method: "POST", form }));
      formElement.reset();
      setFileName(null);
      setShowLink(false);
      setLength(0);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-4">
      <form onSubmit={submit} className="grid gap-3">
        <label className="sr-only" htmlFor="post-body">
          Escribe en #{channel.slug}
        </label>
        <textarea
          id="post-body"
          name="body"
          rows={3}
          maxLength={POST_MAX_CHARS}
          aria-describedby="post-count"
          onChange={(event) => setLength(event.target.value.length)}
          placeholder={`Comparte un hallazgo en #${channel.slug}…`}
          className="w-full resize-y rounded-[var(--radius-field)] border border-line bg-surface px-3.5 py-2.5 focus:border-secondary focus:outline-none focus:ring-3 focus:ring-primary/25"
        />
        {showLink && (
          <input
            name="link_url"
            type="url"
            aria-label="Link"
            placeholder="https://…"
            className="rounded-[var(--radius-field)] border border-line px-3.5 py-2 focus:border-secondary focus:outline-none"
          />
        )}
        {error && <p role="alert" className="text-sm font-semibold text-accent-2">{error}</p>}
        <div className="flex flex-wrap items-center gap-2">
          <label className="inline-flex min-h-10 cursor-pointer items-center gap-1.5 rounded-full px-3 text-sm font-semibold text-link hover:bg-line/50">
            <ImageSquare weight="bold" aria-hidden /> {fileName ?? "Imagen"}
            <input
              type="file"
              name="image"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
            />
          </label>
          <button
            type="button"
            onClick={() => setShowLink((v) => !v)}
            className="inline-flex min-h-10 items-center gap-1.5 rounded-full px-3 text-sm font-semibold text-link hover:bg-line/50"
          >
            <LinkSimple weight="bold" aria-hidden /> Link
          </button>
          <span
            id="post-count"
            aria-live="polite"
            className={`ml-auto text-xs tabular-nums ${length > POST_MAX_CHARS - 32 ? "font-semibold text-accent-2" : "text-muted"}`}
          >
            {length}/{POST_MAX_CHARS}
          </span>
          <Button type="submit" loading={busy} icon={<PaperPlaneRight weight="fill" />}>
            Publicar
          </Button>
        </div>
      </form>
    </Card>
  );
}

function Comments({ post, moderator, onCount }: { post: PostOut; moderator: boolean; onCount: (n: number) => void }) {
  const [items, setItems] = useState<CommentOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      api<Page<CommentOut>>(`/posts/${post.id}/comments`, { query: { limit: 50 } })
        .then((page) => setItems(page.items))
        .catch((err) => setError(errorMessage(err))),
    [post.id],
  );
  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const body = String(new FormData(formElement).get("body")).trim();
    if (!body) return;
    try {
      const comment = await api<CommentOut>(`/posts/${post.id}/comments`, { method: "POST", json: { body } });
      const next = [...(items ?? []), comment];
      setItems(next);
      onCount(next.length);
      formElement.reset();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function hide(comment: CommentOut) {
    if (!window.confirm("¿Ocultar este comentario?")) return;
    try {
      await api(`/comments/${comment.id}/hide`, { method: "POST" });
      const next = (items ?? []).map((c) => (c.id === comment.id ? { ...c, body: "", is_hidden: true } : c));
      setItems(next);
      onCount(next.filter((c) => !c.is_hidden).length);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="mt-3 grid gap-3 border-t border-line pt-3">
      {error && <p className="text-sm text-accent-2">{error}</p>}
      {!items ? (
        <Skeleton className="h-10" />
      ) : (
        items.map((comment) =>
          comment.is_hidden ? (
            <p key={comment.id} className="flex items-center gap-2 rounded-2xl bg-subtle px-3 py-2 text-sm italic text-muted">
              <EyeSlash aria-hidden /> Comentario oculto por moderación
            </p>
          ) : (
          <div key={comment.id} className="flex gap-2">
            <Avatar user={comment.author} size="sm" />
            <div className="min-w-0 flex-1 rounded-2xl bg-subtle px-3 py-2">
              <p className="text-xs">
                <strong>{comment.author.nickname}</strong> <span className="text-muted">· {timeAgo(comment.created_at)}</span>
              </p>
              <Markdown source={comment.body} className="text-sm" />
            </div>
            {moderator && (
              <button type="button" aria-label="Ocultar comentario" className="self-start rounded-full p-2 text-accent-2 hover:bg-line/50" onClick={() => void hide(comment)}>
                <EyeSlash weight="bold" />
              </button>
            )}
          </div>
          ),
        )
      )}
      <form onSubmit={submit} className="flex gap-2">
        <input
          name="body"
          maxLength={2000}
          aria-label="Escribe un comentario"
          placeholder="Escribe un comentario…"
          className="min-h-10 flex-1 rounded-full border border-line px-4 text-sm focus:border-secondary focus:outline-none"
        />
        <Button type="submit" size="sm" variant="secondary">
          Comentar
        </Button>
      </form>
    </div>
  );
}

function PostCard({ post, channels, moderator, onHidden, onError }: {
  post: PostOut;
  channels: ChannelOut[];
  moderator: boolean;
  onHidden: (id: number) => void;
  onError: (message: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(post.comment_count);
  const channel = channels.find((c) => c.id === post.channel_id);

  async function hide() {
    if (!window.confirm("¿Ocultar esta publicación para todos? Quedará registro de quién la ocultó.")) return;
    try {
      await api(`/posts/${post.id}/hide`, { method: "POST" });
      onHidden(post.id);
    } catch (err) {
      onError(errorMessage(err));
    }
  }

  if (post.is_hidden) {
    return (
      <article className="flex items-center gap-3 rounded-card border border-dashed border-line bg-subtle px-4 py-3 text-sm text-muted">
        <EyeSlash size={20} aria-hidden />
        <p className="flex-1 italic">Mensaje oculto por moderación</p>
        <span className="text-xs">{timeAgo(post.created_at)}</span>
      </article>
    );
  }

  return (
    <article className="rounded-card border border-line bg-surface p-4">
      <header className="flex items-center gap-3">
        <Avatar user={post.author} />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink">{post.author.nickname}</p>
          <p className="text-xs text-muted">
            #{channel?.slug ?? post.channel_slug} · {timeAgo(post.created_at)}
          </p>
        </div>
        {moderator && (
          <button type="button" aria-label="Ocultar publicación" title="Ocultar publicación" className="rounded-full p-2 text-accent-2 hover:bg-line/50" onClick={() => void hide()}>
            <EyeSlash weight="bold" />
          </button>
        )}
      </header>
      <Markdown source={post.body} className="mt-3" />
      {post.image_url?.startsWith("/media/") && (
        <img src={post.image_url} alt="Imagen de la publicación" loading="lazy" className="mt-3 max-h-96 w-full rounded-2xl bg-subtle object-contain" />
      )}
      {post.link_url && (
        <a href={post.link_url} target="_blank" rel="noopener noreferrer nofollow" className="mt-3 inline-flex max-w-full items-center gap-1.5 truncate text-sm font-semibold">
          <LinkSimple weight="bold" aria-hidden /> {post.link_url}
        </a>
      )}
      <footer className="mt-3">
        {/* Reactions and comments share one row; comments open full width below it. */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Reactions post={post} onError={onError} />
          <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-2 text-sm font-semibold text-muted hover:bg-line/50 hover:text-ink">
            <ChatCircle weight="bold" aria-hidden /> {count === 1 ? "1 comentario" : `${count} comentarios`}
          </button>
        </div>
        {open && <Comments post={post} moderator={moderator} onCount={setCount} />}
      </footer>
    </article>
  );
}

/** `clubSlug` set = club-scoped view (/a/:slug/comunidad): only that club's channel, no channel list. */
function CommunityPage({ clubSlug }: { clubSlug?: string }) {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [channels, setChannels] = useState<ChannelOut[] | null>(null);
  const [colors, setColors] = useState<Record<number, string>>({});
  const [posts, setPosts] = useState<PostOut[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const slug = clubSlug ?? params.get("canal") ?? "feed";
  const channel = channels?.find((c) => c.slug === slug) ?? (clubSlug ? undefined : channels?.[0]);
  const channelId = channel?.id;
  const currentId = useRef<number | undefined>(undefined);
  useEffect(() => {
    currentId.current = channelId; // declared before the loading effect, so it runs first
  }, [channelId]);

  useEffect(() => {
    api<ChannelOut[]>("/channels")
      .then(setChannels)
      .catch((err) => setError(errorMessage(err)));
    if (clubSlug) return;
    // Club colors for the channel markers (optional decoration).
    api<Page<AcademyCardOut>>("/academies", { query: { limit: 50 } })
      .then((page) => setColors(Object.fromEntries(page.items.map((a) => [a.id, a.color_primary]))))
      .catch(() => undefined);
  }, [clubSlug]);

  const loadFirst = useCallback(async (id: number) => {
    try {
      const page = await api<Page<PostOut>>(`/channels/${id}/posts`, { query: { limit: 20 } });
      if (currentId.current !== id) return; // user switched channel meanwhile
      setPosts((prev) => {
        if (!prev) return page.items;
        // Periodic refresh: new posts on top; posts we already have take the server's latest state
        // (e.g. hidden by a moderator meanwhile); older pages already loaded stay.
        const fresh = new Map(page.items.map((p) => [p.id, p]));
        const known = new Set(prev.map((p) => p.id));
        return [...page.items.filter((p) => !known.has(p.id)), ...prev.map((p) => fresh.get(p.id) ?? p)];
      });
      setCursor((prev) => prev ?? page.next_cursor);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    if (channelId === undefined) return;
    setPosts(null);
    setCursor(null);
    void loadFirst(channelId);
    // Idle/hidden tabs do not poll (security review: constant load from background tabs).
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void loadFirst(channelId);
    }, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [channelId, loadFirst]);

  async function loadMore() {
    if (!channelId || !cursor) return;
    setLoadingMore(true);
    try {
      const page = await api<Page<PostOut>>(`/channels/${channelId}/posts`, { query: { limit: 20, cursor } });
      setPosts((prev) => [...(prev ?? []), ...page.items.filter((p) => !prev?.some((q) => q.id === p.id))]);
      setCursor(page.next_cursor);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingMore(false);
    }
  }

  if (error && !channels) return <ErrorState message={error} />;
  if (clubSlug && channels && !channel) {
    return <EmptyState title="Este club aún no tiene canal" action={<Link to="/comunidad">Ver toda la comunidad</Link>} />;
  }

  const channelButton = (c: ChannelOut) => {
    const active = c.id === channelId;
    return (
      <button
        key={c.id}
        type="button"
        onClick={() => setParams({ canal: c.slug }, { replace: true })}
        aria-current={active ? "page" : undefined}
        className={`flex min-h-11 w-auto shrink-0 items-center gap-2 rounded-xl px-3 text-left text-sm font-semibold transition lg:w-full ${
          active ? "bg-subtle text-ink ring-1 ring-line" : "text-muted hover:bg-subtle hover:text-ink"
        }`}
      >
        {c.type === "feed" ? (
          <Rss weight="bold" aria-hidden />
        ) : c.type === "academy" ? (
          <span aria-hidden className="size-2.5 rounded-full" style={{ background: (c.academy_id && colors[c.academy_id]) || "var(--academy-primary)" }} />
        ) : (
          <Hash weight="bold" aria-hidden />
        )}
        <span className="truncate">{c.type === "feed" ? "Feed" : c.type === "general" ? "General" : c.slug}</span>
      </button>
    );
  };

  const feed = (
    <section aria-label={`Canal ${channel?.slug ?? ""}`} className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-4">
      {channel && !clubSlug && (
        <div>
          <h2 className="text-xl">{channel.type === "feed" ? "Feed" : `#${channel.slug}`}</h2>
          <p className="text-sm text-muted">
            {channel.type === "feed"
              ? "Lo más reciente de General y de todos los clubes."
              : channel.type === "general"
                ? "Conversación abierta para todo el campus."
                : `Canal del club ${channel.name}.`}
          </p>
        </div>
      )}
      {channel && channel.type !== "feed" && (
        <Composer channel={channel} onPosted={(post) => setPosts((prev) => [post, ...(prev ?? [])])} />
      )}
      {error && <Notice tone="alert">{error}</Notice>}
      {!posts ? (
        <ListSkeleton rows={3} />
      ) : posts.length === 0 ? (
        <EmptyState title="Aún no hay publicaciones" description="Sé la primera persona en compartir algo aquí." />
      ) : (
        posts.map((post, index) => (
          <div key={post.id} className="enter" style={{ "--i": Math.min(index, 8) } as CSSProperties}>
            <PostCard
              post={post}
              channels={channels ?? []}
              moderator={canModerate(user, channels?.find((c) => c.id === post.channel_id))}
              onHidden={(id) =>
                setPosts((prev) =>
                  (prev ?? []).map((p) =>
                    p.id === id ? { ...p, is_hidden: true, body: "", image_url: null, link_url: null, reactions: {}, comment_count: 0 } : p,
                  ),
                )
              }
              onError={setError}
            />
          </div>
        ))
      )}
      {cursor && posts && posts.length > 0 && (
        <Button variant="secondary" className="justify-self-center" loading={loadingMore} onClick={() => void loadMore()}>
          Ver publicaciones anteriores
        </Button>
      )}
    </section>
  );

  if (clubSlug) {
    return (
      <div className="mx-auto grid max-w-3xl gap-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-3xl">Comunidad</h1>
            <p className="text-sm text-muted">{channel ? `Canal del club ${channel.name}.` : "Cargando canal…"}</p>
          </div>
          <Link to="/comunidad" className="text-sm font-semibold">
            Ver toda la comunidad
          </Link>
        </div>
        {feed}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside aria-label="Canales" className="min-w-0 lg:sticky lg:top-24 lg:self-start">
        <h1 className="mb-3 text-3xl">Comunidad</h1>
        {!channels ? (
          <div className="grid gap-2">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : (
          <nav className="flex gap-1 overflow-x-auto pb-1 lg:grid lg:overflow-visible">{channels.map(channelButton)}</nav>
        )}
      </aside>
      {feed}
    </div>
  );
}

function ClubCommunity() {
  const academy = useAcademy();
  return <CommunityPage key={academy.slug} clubSlug={academy.slug} />;
}

export const routes: RouteObject[] = [
  {
    element: (
      <RequireRole>
        <CampusLayout />
      </RequireRole>
    ),
    children: [{ path: "/comunidad", element: <CommunityPage /> }],
  },
  {
    path: "/a/:slug",
    element: (
      <RequireRole>
        <AcademyLayout />
      </RequireRole>
    ),
    children: [{ path: "comunidad", element: <ClubCommunity /> }],
  },
];
