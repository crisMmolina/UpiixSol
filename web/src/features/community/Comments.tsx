// Comments under a post (UPS-011, UPS-035): oldest first, 20 per page with "Ver más comentarios",
// authors delete their own, moderators hide. Every change reports a delta so the post's counter
// (which the 30 s poll keeps in sync with the server) stays right meanwhile.
import { EyeSlash, Trash } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { Avatar, Button, FormMessage, Markdown, Skeleton } from "@/components";
import { api, errorMessage } from "@/lib/api";
import type { CommentOut, Page, PostOut } from "@/lib/types";

import { timeAgo, WRAP } from "./shared";

const PAGE = 20;

async function fetchPages(postId: number, want: number): Promise<{ all: CommentOut[]; next: string | null }> {
  let next: string | null = null;
  let all: CommentOut[] = [];
  do {
    const page: Page<CommentOut> = await api<Page<CommentOut>>(`/posts/${postId}/comments`, {
      query: { limit: PAGE, ...(next ? { cursor: next } : {}) },
    });
    all = [...all, ...page.items];
    next = page.next_cursor;
  } while (next && all.length < want);
  return { all, next };
}

export function Comments({
  post,
  moderator,
  userId,
  onCountChange,
}: {
  post: PostOut;
  moderator: boolean;
  userId: number | undefined;
  onCountChange: (delta: number) => void;
}) {
  const [items, setItems] = useState<CommentOut[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const shown = useRef(0);
  useEffect(() => {
    shown.current = items?.length ?? 0;
  }, [items]);

  /** First page, or as many pages as already shown (a refresh never shortens the list). */
  const load = useCallback(
    () =>
      fetchPages(post.id, Math.max(shown.current, 1))
        .then(({ all, next }) => {
          setItems(all);
          setCursor(next);
        })
        .catch((err) => setError(errorMessage(err))),
    [post.id],
  );

  useEffect(() => {
    void load();
  }, [load]);

  // The poll brought a different count (someone else commented, deleted or a moderator hid one):
  // refresh what is shown so the list matches the counter.
  const serverCount = post.comment_count;
  const seen = useRef(serverCount);
  useEffect(() => {
    if (seen.current === serverCount) return;
    seen.current = serverCount;
    void load();
  }, [serverCount, load]);

  async function loadMore() {
    if (!cursor) return;
    setLoadingMore(true);
    try {
      const page = await api<Page<CommentOut>>(`/posts/${post.id}/comments`, { query: { limit: PAGE, cursor } });
      setItems((prev) => [...(prev ?? []), ...page.items.filter((c) => !prev?.some((p) => p.id === c.id))]);
      setCursor(page.next_cursor);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingMore(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const body = String(new FormData(formElement).get("body")).trim();
    if (!body) return;
    setError(null);
    try {
      const comment = await api<CommentOut>(`/posts/${post.id}/comments`, { method: "POST", json: { body } });
      // With more pages pending, the new comment shows when they are loaded (it is the newest).
      if (!cursor) setItems((prev) => [...(prev ?? []), comment]);
      onCountChange(1);
      formElement.reset();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function hide(comment: CommentOut) {
    if (!window.confirm("¿Ocultar este comentario?")) return;
    setError(null);
    try {
      await api(`/comments/${comment.id}/hide`, { method: "POST" });
      setItems((prev) => (prev ?? []).map((c) => (c.id === comment.id ? { ...c, body: "", is_hidden: true } : c)));
      onCountChange(-1); // hidden comments are not counted
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(comment: CommentOut) {
    if (!window.confirm("¿Borrar tu comentario? No se puede deshacer.")) return;
    setError(null);
    try {
      await api(`/comments/${comment.id}`, { method: "DELETE" });
      setItems((prev) => (prev ?? []).filter((c) => c.id !== comment.id));
      onCountChange(-1);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const iconButton = "grid size-11 shrink-0 place-items-center self-start rounded-full hover:bg-line/50";

  return (
    <div className="mt-3 grid gap-3 border-t border-line pt-3">
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
              <div className={`flex-1 rounded-2xl bg-subtle px-3 py-2 ${WRAP}`}>
                <p className="text-xs">
                  <strong>{comment.author.nickname}</strong> <span className="text-muted">· {timeAgo(comment.created_at)}</span>
                </p>
                <Markdown source={comment.body} className="text-sm" />
              </div>
              {comment.author.id === userId && (
                <button type="button" aria-label="Borrar mi comentario" title="Borrar mi comentario" className={`${iconButton} text-muted hover:text-ink`} onClick={() => void remove(comment)}>
                  <Trash weight="bold" />
                </button>
              )}
              {moderator && (
                <button type="button" aria-label="Ocultar comentario" title="Ocultar comentario" className={`${iconButton} text-accent-2`} onClick={() => void hide(comment)}>
                  <EyeSlash weight="bold" />
                </button>
              )}
            </div>
          ),
        )
      )}
      {cursor && items && (
        <Button variant="ghost" size="sm" className="justify-self-start" loading={loadingMore} onClick={() => void loadMore()}>
          Ver más comentarios
        </Button>
      )}
      <form onSubmit={submit} className="grid gap-1">
        <div className="flex gap-2">
          <input
            name="body"
            maxLength={2000}
            aria-label="Escribe un comentario"
            placeholder="Escribe un comentario…"
            onChange={() => setError(null)}
            className="min-h-10 min-w-0 flex-1 rounded-full border border-line bg-surface px-4 text-sm focus:border-secondary focus:outline-none focus:ring-3 focus:ring-primary/25"
          />
          <Button type="submit" size="sm" variant="secondary">
            Comentar
          </Button>
        </div>
        <FormMessage message={error} lines={{ base: 2, sm: 1 }} />
      </form>
    </div>
  );
}
