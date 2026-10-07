// UPS-018: reactions under each post. Counts come with the post listing; which ones are mine come from
// GET /api/reactions/mine, batched: every PostCard rendered in the same tick shares one request.
// Only reactions somebody used are shown; the rest live behind "Agregar reacción" so an unreacted post
// does not carry a row of five empty circles.
import { Smiley } from "@phosphor-icons/react";
import { useEffect, useState, type KeyboardEvent } from "react";

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
  const [picking, setPicking] = useState(false);
  const counts = latest && latest.base === post.reactions ? latest.counts : post.reactions;
  const shown = KINDS.filter(({ id }) => (counts[id] ?? 0) > 0 || mine?.includes(id));
  const available = KINDS.filter((kind) => !shown.includes(kind));
  const disabled = mine === null || busy !== null;

  useEffect(() => {
    let alive = true;
    void loadMine(post.id).then((kinds) => alive && setMine((current) => current ?? kinds));
    return () => {
      alive = false;
    };
  }, [post.id]);

  async function toggle(kind: string) {
    const pressed = mine?.includes(kind) ?? false;
    setPicking(false);
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

  function closeOnEscape(event: KeyboardEvent) {
    if (event.key === "Escape" && picking) {
      event.stopPropagation();
      setPicking(false);
    }
  }

  return (
    <div role="group" aria-label="Reacciones" className="flex flex-wrap items-center gap-1.5" onKeyDown={closeOnEscape}>
      {shown.map(({ id, emoji, label }) => {
        const total = counts[id] ?? 0;
        const pressed = mine?.includes(id) ?? false;
        return (
          <button
            key={id}
            type="button"
            aria-pressed={pressed}
            aria-label={`${label}: ${total}`}
            title={label}
            disabled={disabled}
            onClick={() => void toggle(id)}
            className={`inline-flex min-h-11 min-w-11 items-center justify-center gap-1 rounded-full border px-3 text-sm font-semibold tabular-nums transition disabled:opacity-60 ${
              pressed ? "border-secondary bg-primary/15 text-ink" : "border-line bg-surface text-muted hover:border-ink hover:text-ink"
            }`}
          >
            <span aria-hidden>{emoji}</span>
            <span aria-hidden>{total}</span>
          </button>
        );
      })}
      {available.length > 0 && (
        <button
          type="button"
          aria-expanded={picking}
          aria-label="Agregar reacción"
          title="Agregar reacción"
          disabled={disabled}
          onClick={() => setPicking((open) => !open)}
          className={`inline-flex min-h-11 min-w-11 items-center justify-center gap-0.5 rounded-full px-2.5 text-muted transition hover:bg-line/50 hover:text-ink disabled:opacity-60 ${
            picking ? "bg-line/50 text-ink" : ""
          }`}
        >
          <Smiley size={20} weight="bold" aria-hidden />
          <span aria-hidden className="text-sm font-bold">+</span>
        </button>
      )}
      {picking && (
        <div className="flex gap-0.5 rounded-full border border-line bg-surface p-0.5 shadow-soft">
          {available.map(({ id, emoji, label }) => (
            <button
              key={id}
              type="button"
              aria-label={label}
              title={label}
              disabled={disabled}
              onClick={() => void toggle(id)}
              className="grid size-11 place-items-center rounded-full text-lg transition hover:bg-line/50 disabled:opacity-60"
            >
              <span aria-hidden>{emoji}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
