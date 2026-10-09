// One post (UPS-011, UPS-025, UPS-035). Hidden posts stay in place as a banner; the card's height
// animates (AnimatedHeight) when it turns into that banner or opens its comments.
import { ChatCircle, EyeSlash, LinkSimple, Trash } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";

import { AnimatedHeight, Avatar, DURATION, EASE_OUT, Markdown } from "@/components";
import { api, errorMessage } from "@/lib/api";
import type { PostOut } from "@/lib/types";

import { Comments } from "./Comments";
import { Reactions } from "./Reactions";
import { timeAgo, WRAP, type CommunityChannel } from "./shared";

export function PostCard({
  post,
  channel,
  moderator,
  userId,
  onHidden,
  onDeleted,
  onError,
}: {
  post: PostOut;
  channel: CommunityChannel | undefined;
  moderator: boolean;
  userId: number | undefined;
  onHidden: (id: number) => void;
  onDeleted: (id: number) => void;
  onError: (message: string) => void;
}) {
  const reduce = useReducedMotion();
  const [open, setOpen] = useState(false);
  // My own changes to the count, valid until the listing refreshes this post (a new object from the poll).
  const [local, setLocal] = useState<{ base: PostOut; count: number } | null>(null);
  const count = local && local.base === post ? local.count : post.comment_count;
  const slug = channel?.slug ?? post.channel_slug;

  async function hide() {
    if (!window.confirm("¿Ocultar esta publicación para todos? Quedará registro de quién la ocultó.")) return;
    try {
      await api(`/posts/${post.id}/hide`, { method: "POST" });
      onHidden(post.id);
    } catch (err) {
      onError(errorMessage(err));
    }
  }

  async function remove() {
    if (!window.confirm("¿Borrar tu publicación? Se borran también sus comentarios y reacciones.")) return;
    try {
      await api(`/posts/${post.id}`, { method: "DELETE" });
      onDeleted(post.id);
    } catch (err) {
      onError(errorMessage(err));
    }
  }

  const fade = reduce ? { duration: 0 } : { duration: DURATION.enter, ease: EASE_OUT };

  return (
    <AnimatedHeight>
      {post.is_hidden ? (
        <motion.article
          key="hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={fade}
          className="flex items-center gap-3 rounded-card border border-dashed border-line bg-subtle px-4 py-3 text-sm text-muted"
        >
          <EyeSlash size={20} aria-hidden className="shrink-0" />
          <div className="flex min-w-0 flex-1 flex-wrap items-baseline justify-between gap-x-3">
            <p className="italic">Mensaje oculto por moderación</p>
            <span className="text-xs">
              #{slug} · publicado {timeAgo(post.created_at)}
            </span>
          </div>
        </motion.article>
      ) : (
        <article className="rounded-card border border-line bg-surface p-4">
          <header className="flex items-center gap-3">
            <Avatar user={post.author} />
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold text-ink">{post.author.nickname}</p>
              <p className="truncate text-xs text-muted">
                #{slug} · {timeAgo(post.created_at)}
              </p>
            </div>
            {post.author.id === userId && (
              <button
                type="button"
                aria-label="Borrar mi publicación"
                title="Borrar mi publicación"
                className="grid size-11 shrink-0 place-items-center rounded-full text-muted hover:bg-line/50 hover:text-ink"
                onClick={() => void remove()}
              >
                <Trash weight="bold" />
              </button>
            )}
            {moderator && (
              <button
                type="button"
                aria-label="Ocultar publicación"
                title="Ocultar publicación"
                className="grid size-11 shrink-0 place-items-center rounded-full text-accent-2 hover:bg-line/50"
                onClick={() => void hide()}
              >
                <EyeSlash weight="bold" />
              </button>
            )}
          </header>
          <Markdown source={post.body} className={`mt-3 ${WRAP}`} />
          {post.image_url?.startsWith("/media/") && (
            <img src={post.image_url} alt="Imagen de la publicación" loading="lazy" className="mt-3 max-h-96 w-full rounded-2xl bg-subtle object-contain" />
          )}
          {post.link_url && (
            <a
              href={post.link_url}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="mt-3 flex w-fit max-w-full items-center gap-1.5 text-sm font-semibold"
            >
              <LinkSimple weight="bold" aria-hidden className="shrink-0" />
              <span className="min-w-0 truncate">{post.link_url}</span>
            </a>
          )}
          <footer className="mt-3">
            {/* Reactions and comments share one row; comments open full width below it. */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Reactions post={post} onError={onError} />
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                aria-expanded={open}
                className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-2 text-sm font-semibold text-muted hover:bg-line/50 hover:text-ink"
              >
                <ChatCircle weight="bold" aria-hidden /> {count === 1 ? "1 comentario" : `${count} comentarios`}
              </button>
            </div>
            {open && (
              <Comments
                post={post}
                moderator={moderator}
                userId={userId}
                onCountChange={(delta) =>
                  setLocal((prev) => ({
                    base: post,
                    count: Math.max(0, (prev && prev.base === post ? prev.count : post.comment_count) + delta),
                  }))
                }
              />
            )}
          </footer>
        </article>
      )}
    </AnimatedHeight>
  );
}
