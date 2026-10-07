// UPS-018: reactions under each post. Counts come with the post listing; which ones are mine come from
// GET /api/reactions/mine, batched: every PostCard rendered in the same tick shares one request.
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { PostOut } from "@/lib/types";

const KINDS = [
  { id: "like", emoji: "👍", label: "Me gusta" },
  { id: "love", emoji: "❤️", label: "Me encanta" },
  { id: "fire", emoji: "🔥", label: "Fuego" },
  { id: "idea", emoji: "💡", label: "Buena idea" },
  { id: "clap", emoji: "👏", label: "Aplausos" },
] as const;
const MAX_IDS = 50;

interface ReactionsOut {
  post_id: number;
  reactions: Record<string, number>;
  mine: string[];
}

// ── Batched loader for "mine" ────────────────────────────────
let queued = new Map<number, ((kinds: string[]) => void)[]>();
let scheduled = false;

function flush() {
  scheduled = false;
  const batch = queued;
  queued = new Map();
  const ids = [...batch.keys()];
  for (let i = 0; i < ids.length; i += MAX_IDS) {
    const chunk = ids.slice(i, i + MAX_IDS);
    api<Record<string, string[]>>("/reactions/mine", { query: { post_ids: chunk.join(",") } })
      .catch(() => ({}) as Record<string, string[]>) // counts still show; toggles start unpressed
      .then((mine) => chunk.forEach((id) => batch.get(id)?.forEach((resolve) => resolve(mine[String(id)] ?? []))));
  }
}

function loadMine(postId: number): Promise<string[]> {
  return new Promise((resolve) => {
    queued.set(postId, [...(queued.get(postId) ?? []), resolve]);
    if (!scheduled) {
      scheduled = true;
      setTimeout(flush, 0);
    }
  });
}

// ── Component ────────────────────────────────────────────────
export function Reactions({ post, onError }: { post: PostOut; onError: (message: string) => void }) {
  const [mine, setMine] = useState<string[] | null>(null); // null until loaded: toggles wait for it
  // Counts from my last toggle, valid only while the listing has not refreshed this post since.
  const [latest, setLatest] = useState<{ base: PostOut["reactions"]; counts: Record<string, number> } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const counts = latest && latest.base === post.reactions ? latest.counts : post.reactions;

  useEffect(() => {
    let alive = true;
    void loadMine(post.id).then((kinds) => alive && setMine((current) => current ?? kinds));
    return () => {
      alive = false;
    };
  }, [post.id]);

  async function toggle(kind: string) {
    const pressed = mine?.includes(kind) ?? false;
    setBusy(kind);
    try {
      const result = await api<ReactionsOut>(`/posts/${post.id}/reactions/${kind}`, { method: pressed ? "DELETE" : "PUT" });
      setMine(result.mine);
      setLatest({ base: post.reactions, counts: result.reactions });
    } catch (err) {
      onError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div role="group" aria-label="Reacciones" className="flex flex-wrap gap-1.5">
      {KINDS.map(({ id, emoji, label }) => {
        const total = counts[id] ?? 0;
        const pressed = mine?.includes(id) ?? false;
        return (
          <button
            key={id}
            type="button"
            aria-pressed={pressed}
            aria-label={`${label}: ${total}`}
            title={label}
            disabled={mine === null || busy !== null}
            onClick={() => void toggle(id)}
            className={`inline-flex min-h-11 min-w-11 items-center justify-center gap-1 rounded-full border px-2.5 text-sm font-semibold tabular-nums transition disabled:opacity-60 ${
              pressed ? "border-secondary bg-primary/15 text-ink" : "border-line bg-surface text-muted hover:border-ink hover:text-ink"
            }`}
          >
            <span aria-hidden>{emoji}</span>
            {total > 0 && <span aria-hidden>{total}</span>}
          </button>
        );
      })}
    </div>
  );
}
