// The block list of the composer: add, edit inline, move up/down and delete (spec 004 §Stories).
import { ArrowDown, ArrowUp, Plus, Trash } from "@phosphor-icons/react";

import { Button } from "@/components/Button";
import { TextArea, TextField } from "@/components/Field";

import { campusUrl, clubUrl, KIND_LABEL, KINDS, MAX_BLOCKS, newDraft, type Draft } from "./blocks";

const iconButton =
  "inline-flex size-11 items-center justify-center rounded-full text-ink transition hover:bg-subtle disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-3";

function Fields({ draft, onChange, clubSlug }: { draft: Draft; onChange: (next: Draft) => void; clubSlug: string | null }) {
  switch (draft.kind) {
    case "heading":
      return <TextField label="Texto del título" value={draft.text} maxLength={120} onChange={(e) => onChange({ ...draft, text: e.target.value.replace(/[\r\n]+/g, " ") })} />;
    case "paragraph":
      return <TextArea label="Texto del párrafo" value={draft.text} maxLength={2000} rows={4} onChange={(e) => onChange({ ...draft, text: e.target.value })} />;
    case "list":
      return (
        <div className="grid gap-2">
          <TextArea label="Elementos de la lista (uno por línea)" value={draft.text} rows={4} onChange={(e) => onChange({ ...draft, text: e.target.value })} />
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input type="checkbox" checked={draft.ordered} onChange={(e) => onChange({ ...draft, ordered: e.target.checked })} className="size-4 accent-[var(--color-link)]" />
            Lista numerada
          </label>
        </div>
      );
    case "button":
      return (
        <div className="grid gap-3">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Botones de ejemplo">
            <Button type="button" size="sm" variant="secondary" onClick={() => onChange({ ...draft, label: "Ir al campus", url: campusUrl() })}>
              Ir al campus
            </Button>
            <Button type="button" size="sm" variant="secondary" disabled={!clubSlug} onClick={() => clubSlug && onChange({ ...draft, label: "Ver el club", url: clubUrl(clubSlug) })}>
              Ver el club
            </Button>
          </div>
          <TextField label="Texto del botón" value={draft.label} maxLength={40} onChange={(e) => onChange({ ...draft, label: e.target.value.replace(/[\r\n]+/g, " ") })} />
          <TextField label="Enlace del botón" type="url" inputMode="url" value={draft.url} placeholder="https://" onChange={(e) => onChange({ ...draft, url: e.target.value })} />
        </div>
      );
    case "divider":
      return <p className="text-sm text-muted">Una línea que separa dos partes del correo.</p>;
  }
}

export function BlockEditor({
  drafts,
  onChange,
  clubSlug,
}: {
  drafts: Draft[];
  onChange: (next: Draft[]) => void;
  /** Slug of the club the "Ver el club" preset links to; null while none applies. */
  clubSlug: string | null;
}) {
  const full = drafts.length >= MAX_BLOCKS;

  function update(index: number, next: Draft) {
    onChange(drafts.map((d, i) => (i === index ? next : d)));
  }
  function move(index: number, by: -1 | 1) {
    const next = [...drafts];
    [next[index], next[index + by]] = [next[index + by], next[index]];
    onChange(next);
  }

  return (
    <div className="grid gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-semibold">Mensaje</h3>
        <p className="text-xs text-muted">
          Formato: <code>**negritas**</code> · <code>*cursivas*</code> · <code>[texto](https://enlace)</code>
        </p>
      </div>
      <ul aria-label="Bloques del correo" className="grid divide-y divide-line border-y border-line">
        {drafts.map((draft, index) => (
          <li key={draft.id} aria-label={`Bloque ${index + 1}: ${KIND_LABEL[draft.kind]}`} className="grid gap-3 py-4">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-muted">{KIND_LABEL[draft.kind]}</span>
              <div className="flex items-center">
                <button type="button" className={iconButton} aria-label="Mover arriba" disabled={index === 0} onClick={() => move(index, -1)}>
                  <ArrowUp weight="bold" />
                </button>
                <button type="button" className={iconButton} aria-label="Mover abajo" disabled={index === drafts.length - 1} onClick={() => move(index, 1)}>
                  <ArrowDown weight="bold" />
                </button>
                <button type="button" className={iconButton} aria-label="Eliminar bloque" onClick={() => onChange(drafts.filter((_, i) => i !== index))}>
                  <Trash weight="bold" />
                </button>
              </div>
            </div>
            <Fields draft={draft} onChange={(next) => update(index, next)} clubSlug={clubSlug} />
          </li>
        ))}
      </ul>
      <div role="group" aria-label="Agregar bloque" className="flex flex-wrap gap-2">
        {KINDS.map(({ kind, label, soon }) => (
          <Button
            key={kind}
            type="button"
            size="sm"
            variant="secondary"
            icon={<Plus weight="bold" />}
            disabled={soon || full}
            title={soon ? "Próximamente" : undefined}
            onClick={() => kind !== "event" && kind !== "image" && onChange([...drafts, newDraft(kind)])}
          >
            {`Agregar ${label}`}
          </Button>
        ))}
      </div>
      {full && <p className="text-sm text-muted">{`Un correo admite hasta ${MAX_BLOCKS} bloques.`}</p>}
    </div>
  );
}
