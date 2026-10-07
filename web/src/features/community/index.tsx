// Flow step 4 (UPS-011): Discord-style community — Feed, General and one channel per academy.
// No realtime in v1: the open channel refreshes every 30 s (IDEA §9).
import { ChatCircle, EyeSlash, Hash, ImageSquare, LinkSimple, PaperPlaneRight, Rss } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useSearchParams, type RouteObject } from "react-router";

import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Markdown } from "@/components/Markdown";
import { Skeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState, Notice } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { AcademyCardOut, ChannelOut, CommentOut, Page, PostOut, UserMe } from "@/lib/types";
import { CampusLayout } from "@/layouts";

import { Reactions } from "./Reactions";

export const order = 35;

const REFRESH_MS = 30_000;
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
          maxLength={5000}
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
          <Button type="submit" loading={busy} icon={<PaperPlaneRight weight="fill" />} className="ml-auto">
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
      const next = (items ?? []).filter((c) => c.id !== comment.id);
      setItems(next);
      onCount(next.length);
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
        items.map((comment) => (
          <div key={comment.id} className="flex gap-2">
            <Avatar user={comment.author} size="sm" />
            <div className="min-w-0 flex-1 rounded-2xl bg-bg px-3 py-2">
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
        ))
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

  return (
    <article className="rounded-card border border-line bg-surface p-4 shadow-soft">
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
        <img src={post.image_url} alt="Imagen de la publicación" loading="lazy" className="mt-3 max-h-96 w-full rounded-2xl object-contain bg-bg" />
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

function CommunityPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [channels, setChannels] = useState<ChannelOut[] | null>(null);
  const [colors, setColors] = useState<Record<number, string>>({});
  const [posts, setPosts] = useState<PostOut[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const slug = params.get("canal") ?? "feed";
  const channel = channels?.find((c) => c.slug === slug) ?? channels?.[0];
  const channelId = channel?.id;
  const currentId = useRef<number | undefined>(undefined);
  useEffect(() => {
    currentId.current = channelId; // declared before the loading effect, so it runs first
  }, [channelId]);

  useEffect(() => {
    api<ChannelOut[]>("/channels")
      .then(setChannels)
      .catch((err) => setError(errorMessage(err)));
    // Academy colors for the channel dots (optional decoration).
    api<Page<AcademyCardOut>>("/academies", { query: { limit: 50 } })
      .then((page) => setColors(Object.fromEntries(page.items.map((a) => [a.id, a.color_primary]))))
      .catch(() => undefined);
  }, []);

  const loadFirst = useCallback(async (id: number) => {
    try {
      const page = await api<Page<PostOut>>(`/channels/${id}/posts`, { query: { limit: 20 } });
      if (currentId.current !== id) return; // user switched channel meanwhile
      setPosts((prev) => {
        if (!prev) return page.items;
        // Periodic refresh: prepend only posts we do not have yet; keep older pages already loaded.
        const known = new Set(prev.map((p) => p.id));
        return [...page.items.filter((p) => !known.has(p.id)), ...prev];
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

  const channelButton = (c: ChannelOut) => {
    const active = c.id === channelId;
    return (
      <button
        key={c.id}
        type="button"
        onClick={() => setParams({ canal: c.slug }, { replace: true })}
        aria-current={active ? "page" : undefined}
        className={`flex min-h-11 w-auto shrink-0 items-center gap-2 rounded-xl px-3 text-left text-sm font-semibold lg:w-full ${
          active ? "bg-primary/15 text-ink ring-1 ring-primary/40" : "text-muted hover:bg-line/50 hover:text-ink"
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

  return (
    <div className="grid gap-6 lg:grid-cols-[15rem_1fr]">
      <aside aria-label="Canales" className="lg:sticky lg:top-24 lg:self-start">
        <h1 className="mb-3 text-2xl">Comunidad</h1>
        {!channels ? (
          <Skeleton className="h-32" />
        ) : (
          <nav className="flex gap-1 overflow-x-auto pb-1 lg:grid lg:overflow-visible">{channels.map(channelButton)}</nav>
        )}
      </aside>

      <section aria-label={`Canal ${channel?.slug ?? ""}`} className="grid min-w-0 content-start gap-4">
        {channel && (
          <div>
            <h2 className="text-xl">{channel.type === "feed" ? "Feed" : `#${channel.slug}`}</h2>
            <p className="text-sm text-muted">
              {channel.type === "feed"
                ? "Lo más reciente de General y de todas las academias. Se actualiza cada 30 segundos."
                : channel.type === "general"
                  ? "Conversación abierta para todo el club."
                  : `Canal de la academia ${channel.name}.`}
            </p>
          </div>
        )}
        {channel && channel.type !== "feed" && (
          <Composer channel={channel} onPosted={(post) => setPosts((prev) => [post, ...(prev ?? [])])} />
        )}
        {channel?.type === "feed" && <Notice>Para publicar, elige General o el canal de una academia.</Notice>}
        {error && <Notice tone="alert">{error}</Notice>}
        {!posts ? (
          <>
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </>
        ) : posts.length === 0 ? (
          <EmptyState title="Aún no hay publicaciones" description="Sé la primera persona en compartir algo aquí." />
        ) : (
          posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              channels={channels ?? []}
              moderator={canModerate(user, channels?.find((c) => c.id === post.channel_id))}
              onHidden={(id) => setPosts((prev) => (prev ?? []).filter((p) => p.id !== id))}
              onError={setError}
            />
          ))
        )}
        {cursor && posts && posts.length > 0 && (
          <Button variant="secondary" className="justify-self-center" loading={loadingMore} onClick={() => void loadMore()}>
            Ver publicaciones anteriores
          </Button>
        )}
      </section>
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
    children: [{ path: "/comunidad", element: <CommunityPage /> }],
  },
];
