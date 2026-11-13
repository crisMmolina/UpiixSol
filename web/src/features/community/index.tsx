// Flow step 4 (UPS-011, redesign UPS-025): Discord-style community with Feed, General and one channel
// per club. Inside a club (/a/:slug/comunidad) only that club's channel is shown, in the club layout.
// Hidden posts/comments stay in place as "Mensaje oculto". No realtime in v1: refresh every 30 s.
// UPS-035: switching channel keeps the current list (dimmed) until the new one arrives, then swaps it and
// scrolls back to the top; a post only lands in the list of its own channel (or the Feed).
import { Hash, Rss } from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { Link, useSearchParams, type RouteObject } from "react-router";

import { Button, DURATION, EASE_IN, Notice } from "@/components";
import { EmptyState, ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import { RequireRole, useAuth } from "@/lib/auth";
import type { AcademyCardOut, Page, PostOut } from "@/lib/types";
import { AcademyLayout, CampusLayout, useAcademy } from "@/layouts";

import { Composer } from "./Composer";
import { PostCard } from "./PostCard";
import { canModerate, type CommunityChannel } from "./shared";
import { ChannelHeadingSkeleton, ChannelNavSkeleton, ComposerSkeleton, PostListSkeleton } from "./Skeletons";

export const order = 35;

const REFRESH_MS = 30_000;

/** The list on screen and the channel it belongs to (may lag the selected one while switching). */
interface View {
  channelId: number;
  posts: PostOut[];
  cursor: string | null;
}

function JoinClub({ channel, academySlug, onJoined }: { channel: CommunityChannel; academySlug: string | undefined; onJoined: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function join() {
    if (!academySlug) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/academies/${academySlug}/enroll`, { method: "POST" });
      onJoined();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }
  return (
    <Notice
      action={
        academySlug && (
          <Button size="sm" variant="secondary" loading={busy} onClick={() => void join()}>
            Unirme al club
          </Button>
        )
      }
    >
      {error ?? `Para publicar en #${channel.slug} únete al club ${channel.name}. Puedes leer y comentar sin unirte.`}
    </Notice>
  );
}

/** `clubSlug` set = club-scoped view (/a/:slug/comunidad): only that club's channel, no channel list. */
function CommunityPage({ clubSlug }: { clubSlug?: string }) {
  const { user } = useAuth();
  const reduce = useReducedMotion();
  const [params, setParams] = useSearchParams();
  const [channels, setChannels] = useState<CommunityChannel[] | null>(null);
  const [clubs, setClubs] = useState<Record<number, { slug: string; color: string }>>({});
  const [view, setView] = useState<View | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const top = useRef<HTMLDivElement>(null);

  const slug = clubSlug ?? params.get("canal") ?? "feed";
  const selected = channels?.find((c) => c.slug === slug) ?? (clubSlug ? undefined : channels?.[0]);
  const channelId = selected?.id;
  const shown = channels?.find((c) => c.id === view?.channelId) ?? selected; // what the list belongs to
  const switching = view !== null && channelId !== undefined && view.channelId !== channelId;
  const currentId = useRef<number | undefined>(undefined);
  useEffect(() => {
    currentId.current = channelId; // declared before the loading effect, so it runs first
  }, [channelId]);

  const loadChannels = useCallback(() => {
    api<CommunityChannel[]>("/channels")
      .then(setChannels)
      .catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(() => {
    loadChannels();
    if (clubSlug) return;
    // Club colors for the channel markers (optional decoration) and slugs for "Unirme al club".
    api<Page<AcademyCardOut>>("/academies", { query: { limit: 50 } })
      .then((page) => setClubs(Object.fromEntries(page.items.map((a) => [a.id, { slug: a.slug, color: a.color_primary }]))))
      .catch(() => undefined);
  }, [clubSlug, loadChannels]);

  const loadFirst = useCallback(
    (id: number) =>
      api<Page<PostOut>>(`/channels/${id}/posts`, { query: { limit: 20 } })
        .then((page) => {
          if (currentId.current !== id) return; // user switched channel meanwhile
          setView((prev) => {
            if (!prev || prev.channelId !== id) return { channelId: id, posts: page.items, cursor: page.next_cursor };
            // Periodic refresh: new posts on top; posts we already have take the server's latest state
            // (e.g. hidden by a moderator meanwhile); older pages already loaded stay.
            const fresh = new Map(page.items.map((p) => [p.id, p]));
            const known = new Set(prev.posts.map((p) => p.id));
            const posts = [...page.items.filter((p) => !known.has(p.id)), ...prev.posts.map((p) => fresh.get(p.id) ?? p)];
            return { ...prev, posts, cursor: prev.cursor ?? page.next_cursor };
          });
          setError(null);
        })
        .catch((err) => setError(errorMessage(err))),
    [],
  );

  useEffect(() => {
    if (channelId === undefined) return;
    void loadFirst(channelId);
    // Idle/hidden tabs do not poll (security review: constant load from background tabs).
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void loadFirst(channelId);
    }, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [channelId, loadFirst]);

  // A new channel replaced the list: if the reader was further down, bring the page back to its top
  // (smooth, or instant with reduced motion through the global scroll-behavior rule).
  const shownId = view?.channelId;
  const previousShown = useRef(shownId);
  useEffect(() => {
    if (previousShown.current === shownId) return;
    const switched = previousShown.current !== undefined;
    previousShown.current = shownId;
    if (switched && top.current && top.current.getBoundingClientRect().top < 0) {
      window.scrollTo({ top: 0 });
    }
  }, [shownId]);

  async function loadMore() {
    if (!view?.cursor) return;
    const { channelId: id, cursor } = view;
    setLoadingMore(true);
    try {
      const page = await api<Page<PostOut>>(`/channels/${id}/posts`, { query: { limit: 20, cursor } });
      setView((prev) => {
        if (!prev || prev.channelId !== id) return prev; // switched meanwhile
        const known = new Set(prev.posts.map((p) => p.id));
        return { ...prev, posts: [...prev.posts, ...page.items.filter((p) => !known.has(p.id))], cursor: page.next_cursor };
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingMore(false);
    }
  }

  function addPost(post: PostOut) {
    setView((prev) => {
      if (!prev) return prev;
      const listed = channels?.find((c) => c.id === prev.channelId);
      // Only into its own channel's list or the Feed; the list on screen may belong to another channel by now.
      if (prev.channelId !== post.channel_id && listed?.type !== "feed") return prev;
      return { ...prev, posts: [post, ...prev.posts.filter((p) => p.id !== post.id)] };
    });
  }

  function updatePosts(change: (posts: PostOut[]) => PostOut[]) {
    setView((prev) => (prev ? { ...prev, posts: change(prev.posts) } : prev));
  }

  if (error && !channels) return <ErrorState message={error} />;
  if (clubSlug && channels && !selected) {
    return <EmptyState title="Este club aún no tiene canal" action={<Link to="/comunidad">Ver toda la comunidad</Link>} />;
  }

  const channelButton = (c: CommunityChannel) => {
    const active = c.id === channelId;
    const loading = active && switching;
    return (
      <button
        key={c.id}
        type="button"
        onClick={() => setParams({ canal: c.slug }, { replace: true })}
        aria-current={active ? "page" : undefined}
        aria-busy={loading || undefined}
        className={`flex min-h-11 w-auto shrink-0 items-center gap-2 rounded-xl px-3 text-left text-sm font-semibold transition lg:w-full ${
          active ? "bg-subtle text-ink ring-1 ring-line" : "text-muted hover:bg-subtle hover:text-ink"
        }`}
      >
        {c.type === "feed" ? (
          <Rss weight="bold" aria-hidden />
        ) : c.type === "academy" ? (
          <span aria-hidden className="size-2.5 rounded-full" style={{ background: (c.academy_id && clubs[c.academy_id]?.color) || "var(--academy-primary)" }} />
        ) : (
          <Hash weight="bold" aria-hidden />
        )}
        <span className="truncate">{c.type === "feed" ? "Feed" : c.type === "general" ? "General" : c.slug}</span>
        {/* Fixed slot: the spinner never changes the button's width. */}
        <span aria-hidden className={`ml-auto size-3 shrink-0 rounded-full border-2 border-current border-t-transparent ${loading ? "animate-spin" : "invisible"}`} />
      </button>
    );
  };

  const exit = reduce ? { duration: 0 } : { duration: DURATION.exit, ease: EASE_IN };
  const posts = view?.posts;
  const academySlug = shown?.academy_id ? (clubSlug ?? clubs[shown.academy_id]?.slug) : undefined;

  const feed = (
    <section aria-label={`Canal ${shown?.slug ?? ""}`} aria-busy={switching || undefined} className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-4">
      {!shown && (
        <>
          {!clubSlug && <ChannelHeadingSkeleton />}
          {slug !== "feed" && <ComposerSkeleton />}
        </>
      )}
      {shown && !clubSlug && (
        <div>
          <h2 className="text-xl">{shown.type === "feed" ? "Feed" : `#${shown.slug}`}</h2>
          <p className="text-sm text-muted">
            {shown.type === "feed"
              ? "Lo más reciente de General y de todos los clubes."
              : shown.type === "general"
                ? "Conversación abierta para todo el campus."
                : `Canal del club ${shown.name}.`}
          </p>
        </div>
      )}
      {shown && shown.type !== "feed" && (
        shown.can_post === false ? (
          <JoinClub key={`join-${shown.id}`} channel={shown} academySlug={academySlug} onJoined={loadChannels} />
        ) : (
          <Composer key={`composer-${shown.id}`} channel={shown} onPosted={addPost} />
        )
      )}
      {error && <Notice tone="alert">{error}</Notice>}
      {!posts ? (
        <PostListSkeleton />
      ) : posts.length === 0 ? (
        <EmptyState title="Aún no hay publicaciones" description="Sé la primera persona en compartir algo aquí." />
      ) : (
        // While switching, the old list stays (dimmed, inert) under its own heading until the new one arrives.
        // Keyed by channel: a new channel replaces the list at once (no exit animation for every old post).
        <div
          key={`list-${view?.channelId}`}
          className={`-mb-4 grid grid-cols-[minmax(0,1fr)] transition-opacity duration-200 ${switching ? "pointer-events-none opacity-50" : ""}`}
          inert={switching || undefined}
        >
          <AnimatePresence initial={false}>
            {posts.map((post, index) => (
              <motion.div
                key={post.id}
                exit={{ height: 0, opacity: 0, transition: exit }}
                className="enter overflow-y-clip pb-4"
                style={{ "--i": Math.min(index, 8) } as CSSProperties}
              >
                <PostCard
                  post={post}
                  channel={channels?.find((c) => c.id === post.channel_id)}
                  moderator={canModerate(user, channels?.find((c) => c.id === post.channel_id))}
                  userId={user?.id}
                  onHidden={(id) =>
                    updatePosts((list) =>
                      list.map((p) =>
                        p.id === id ? { ...p, is_hidden: true, body: "", image_url: null, link_url: null, reactions: {}, comment_count: 0 } : p,
                      ),
                    )
                  }
                  onDeleted={(id) => updatePosts((list) => list.filter((p) => p.id !== id))}
                  onError={setError}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
      {view?.cursor && posts && posts.length > 0 && (
        <Button variant="secondary" className="justify-self-center" loading={loadingMore} disabled={switching} onClick={() => void loadMore()}>
          Ver publicaciones anteriores
        </Button>
      )}
    </section>
  );

  if (clubSlug) {
    return (
      <div ref={top} className="mx-auto grid max-w-3xl gap-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-3xl">Comunidad</h1>
            <p className="text-sm text-muted">{selected ? `Canal del club ${selected.name}.` : "Cargando canal…"}</p>
          </div>
          <Link to="/comunidad" className="inline-flex min-h-11 items-center text-sm font-semibold">
            Ver toda la comunidad
          </Link>
        </div>
        {feed}
      </div>
    );
  }

  return (
    <div ref={top} className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside aria-label="Canales" className="min-w-0 lg:sticky lg:top-24 lg:self-start">
        <h1 className="mb-3 text-3xl">Comunidad</h1>
        {!channels ? (
          <ChannelNavSkeleton />
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
