// Image block (spec 004 §Images): upload png/jpg/webp ≤ 5 MB, required alt text, optional link.
import { useId, useState } from "react";

import { Button } from "@/components/Button";
import { TextField } from "@/components/Field";
import { ProgressBar } from "@/components/ProgressBar";
import { apiUpload, errorMessage } from "@/lib/api";

import type { Draft } from "./blocks";

type ImageDraft = Extract<Draft, { kind: "image" }>;

const MAX_BYTES = 5 * 1024 * 1024;
const TYPES = ["image/png", "image/jpeg", "image/webp"];

export function ImageBlockEditor({ draft, onChange, cover }: { draft: ImageDraft; onChange: (next: Draft) => void; cover: string | null }) {
  const inputId = useId();
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function upload(file: File | undefined) {
    if (!file) return;
    if (!TYPES.includes(file.type)) return setError("Solo se aceptan imágenes PNG, JPG o WebP.");
    if (file.size > MAX_BYTES) return setError("La imagen pesa más de 5 MB. Elige una más ligera.");
    setError(null);
    setProgress(0);
    const form = new FormData();
    form.append("file", file);
    try {
      const { url } = await apiUpload<{ url: string }>("/mail/images", form, setProgress);
      onChange({ ...draft, url });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setProgress(null);
    }
  }

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <input id={inputId} type="file" accept={TYPES.join(",")} aria-label="Subir imagen" className="sr-only" disabled={progress !== null} onChange={(e) => { void upload(e.target.files?.[0]); e.target.value = ""; }} />
        <Button type="button" size="sm" variant="secondary" disabled={progress !== null} onClick={() => document.getElementById(inputId)?.click()}>
          {draft.url ? "Cambiar imagen" : "Elegir imagen"}
        </Button>
        {cover && (
          <Button type="button" size="sm" variant="secondary" disabled={progress !== null} onClick={() => { setError(null); onChange({ ...draft, url: cover }); }}>
            Usar la portada del evento
          </Button>
        )}
        <span className="text-xs text-muted">PNG, JPG o WebP · hasta 5 MB</span>
      </div>
      {progress !== null && <ProgressBar percent={progress} label="Subiendo imagen" size="sm" />}
      {error && (
        <p role="alert" className="text-sm font-semibold text-danger">
          {error}
        </p>
      )}
      {draft.url && <img src={draft.url} alt="Imagen subida" className="max-h-48 w-auto max-w-full justify-self-start rounded-xl border border-line" />}
      <TextField label="Texto alternativo de la imagen" value={draft.alt} maxLength={200} hint="Describe la imagen para quien no puede verla." onChange={(e) => onChange({ ...draft, alt: e.target.value.replace(/[\r\n]+/g, " ") })} />
      <TextField label="Enlace de la imagen (opcional)" type="url" inputMode="url" value={draft.link} placeholder="https://" onChange={(e) => onChange({ ...draft, link: e.target.value })} />
    </div>
  );
}
