// Post composer (UPS-011, UPS-035): the error has a reserved line under the buttons, and the link field
// and the image preview grow in (Reveal) instead of pushing "Publicar" at once.
import { ImageSquare, LinkSimple, PaperPlaneRight, X } from "@phosphor-icons/react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button, Card, FormMessage } from "@/components";
import { api, errorMessage } from "@/lib/api";
import type { PostOut } from "@/lib/types";

import { Reveal } from "./Reveal";
import type { CommunityChannel } from "./shared";

const POST_MAX_CHARS = 512; // same limit as the API (app/schemas/community.py)

export function Composer({ channel, onPosted }: { channel: CommunityChannel; onPosted: (post: PostOut) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showLink, setShowLink] = useState(false);
  const [image, setImage] = useState<{ name: string; url: string } | null>(null);
  const [length, setLength] = useState(0);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => () => {
    // Later than the preview's exit animation, which still shows the old image.
    if (image) window.setTimeout(() => URL.revokeObjectURL(image.url), 1000);
  }, [image]);

  function pickImage(file: File | undefined) {
    setError(null);
    setImage(file ? { name: file.name, url: URL.createObjectURL(file) } : null);
  }

  function clearImage() {
    if (fileInput.current) fileInput.current.value = "";
    setImage(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    if (!String(form.get("body")).trim()) return setError("Escribe algo antes de publicar.");
    const file = form.get("image") as File | null;
    if (!file || file.size === 0) form.delete("image");
    if (!String(form.get("link_url") ?? "").trim()) form.delete("link_url");
    setBusy(true);
    setError(null);
    try {
      // The channel is the one this composer was rendered for: switching channels remounts it.
      onPosted(await api<PostOut>(`/channels/${channel.id}/posts`, { method: "POST", form }));
      formElement.reset();
      setImage(null);
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
      <form onSubmit={submit} className="grid">
        <label className="sr-only" htmlFor="post-body">
          Escribe en #{channel.slug}
        </label>
        <textarea
          id="post-body"
          name="body"
          rows={3}
          maxLength={POST_MAX_CHARS}
          aria-describedby="post-count post-message"
          onChange={(event) => {
            setLength(event.target.value.length);
            setError(null);
          }}
          placeholder={`Comparte un hallazgo en #${channel.slug}…`}
          className="w-full resize-y rounded-[var(--radius-field)] border border-line bg-surface px-3.5 py-2.5 focus:border-secondary focus:outline-none focus:ring-3 focus:ring-primary/25"
        />
        <Reveal show={showLink}>
          <div className="pt-3 pb-1">
            <input
              name="link_url"
              type="url"
              aria-label="Link"
              placeholder="https://…"
              className="w-full rounded-[var(--radius-field)] border border-line bg-surface px-3.5 py-2 focus:border-secondary focus:outline-none focus:ring-3 focus:ring-primary/25"
            />
          </div>
        </Reveal>
        <Reveal show={image !== null}>
          {image && (
            <div className="flex items-center gap-3 pt-3 pb-1">
              <img src={image.url} alt="Vista previa de la imagen" className="size-16 shrink-0 rounded-xl border border-line bg-subtle object-cover" />
              <p className="min-w-0 flex-1 truncate text-sm text-muted">{image.name}</p>
              <button
                type="button"
                onClick={clearImage}
                aria-label="Quitar imagen"
                title="Quitar imagen"
                className="grid size-11 shrink-0 place-items-center rounded-full text-muted hover:bg-line/50 hover:text-ink"
              >
                <X weight="bold" aria-hidden />
              </button>
            </div>
          )}
        </Reveal>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {/* The real input is visually hidden: the label shows its keyboard focus. */}
          <label className="inline-flex min-h-11 min-w-0 max-w-full cursor-pointer items-center gap-1.5 rounded-full px-3 text-sm font-semibold text-link outline-offset-2 hover:bg-line/50 has-[input:focus-visible]:outline-3 has-[input:focus-visible]:outline-secondary">
            <ImageSquare weight="bold" aria-hidden className="shrink-0" /> Imagen
            <input
              ref={fileInput}
              type="file"
              name="image"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={(e) => pickImage(e.target.files?.[0])}
            />
          </label>
          <button
            type="button"
            onClick={() => setShowLink((v) => !v)}
            aria-expanded={showLink}
            className={`inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm font-semibold text-link hover:bg-line/50 ${showLink ? "bg-line/50" : ""}`}
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
        <FormMessage id="post-message" message={error} lines={{ base: 2, sm: 1 }} className="mt-2" />
      </form>
    </Card>
  );
}
