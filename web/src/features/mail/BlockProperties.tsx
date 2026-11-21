// Properties of the selected button, event or image (spec 005 §Canvas): a side panel beside the canvas on desktop,
// a bottom sheet on phones. Exactly one instance is mounted (the caller picks the container), so labels stay unique
// and the event list is fetched once. Text blocks have no panel: they are edited on the email.
import { CopySimple, Trash, X } from "@phosphor-icons/react";
import { useEffect, useRef, type ReactNode } from "react";

import { Button } from "@/components/Button";
import { TextField } from "@/components/Field";

import { EventBlockEditor } from "./EventBlockEditor";
import { ImageBlockEditor } from "./ImageBlockEditor";
import { campusUrl, clubUrl, KIND_LABEL, type Draft } from "./blocks";

export const HAS_PROPERTIES = new Set<Draft["kind"]>(["button", "event", "image"]);

type Props = {
  draft: Draft;
  onChange: (next: Draft) => void;
  clubSlug: string | null;
  eventsAcademy: string | null | undefined;
  cover: string | null;
};

function Fields({ draft, onChange, clubSlug, eventsAcademy, cover }: Props) {
  switch (draft.kind) {
    case "button":
      return (
        <div className="grid gap-4">
          <TextField label="Texto del botón" value={draft.label} maxLength={40} onChange={(e) => onChange({ ...draft, label: e.target.value.replace(/[\r\n]+/g, " ") })} />
          <TextField label="Enlace del botón" type="url" inputMode="url" value={draft.url} placeholder="https://" onChange={(e) => onChange({ ...draft, url: e.target.value })} />
          <div className="grid gap-2">
            <p className="text-xs font-semibold text-muted">Enlaces rápidos</p>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Botones de ejemplo">
              <Button type="button" size="sm" variant="secondary" onClick={() => onChange({ ...draft, label: "Ir al campus", url: campusUrl() })}>
                Ir al campus
              </Button>
              <Button type="button" size="sm" variant="secondary" disabled={!clubSlug} onClick={() => clubSlug && onChange({ ...draft, label: "Ver el club", url: clubUrl(clubSlug) })}>
                Ver el club
              </Button>
            </div>
          </div>
        </div>
      );
    case "event":
      return <EventBlockEditor draft={draft} onChange={onChange} academy={eventsAcademy} />;
    case "image":
      return <ImageBlockEditor draft={draft} onChange={onChange} cover={cover} />;
    default:
      return null;
  }
}

function Header({ title, onClose }: { title: string; onClose?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      {onClose && (
        <button type="button" aria-label="Cerrar propiedades" onClick={onClose} className="grid size-11 place-items-center rounded-full hover:bg-subtle focus-visible:outline-3">
          <X weight="bold" />
        </button>
      )}
    </div>
  );
}

export function BlockProperties({
  draft,
  wide,
  autoFocus,
  onClose,
  onDuplicate,
  onDelete,
  canDuplicate,
  problem,
  ...props
}: Omit<Props, "draft"> & {
  /** The selected block, or null (the desktop panel then explains what it is for; phones show nothing). */
  draft: Draft | null;
  wide: boolean;
  /** Focus the first field (a block just inserted). */
  autoFocus: boolean;
  onClose: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  canDuplicate: boolean;
  problem: string | null;
}) {
  const panel = useRef<HTMLElement>(null);
  const shown = draft !== null && HAS_PROPERTIES.has(draft.kind) ? draft : null;

  useEffect(() => {
    if (!shown || !autoFocus) return;
    const root = panel.current;
    (root?.querySelector<HTMLElement>("input:not([type=radio]):not([type=file]), textarea") ?? root?.querySelector<HTMLElement>("input, button:not([aria-label='Cerrar propiedades'])"))?.focus();
    // Only when a new block opens the panel, not on every edit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shown?.id, autoFocus]);

  const body: ReactNode = shown && (
    <>
      <Header title={KIND_LABEL[shown.kind]} onClose={onClose} />
      <Fields draft={shown} {...props} />
      {problem && <p className="text-sm font-semibold text-danger">{problem}</p>}
      <div className="flex flex-wrap gap-2 border-t border-line pt-4">
        <Button type="button" size="sm" variant="secondary" icon={<CopySimple weight="bold" />} disabled={!canDuplicate} onClick={onDuplicate}>
          Duplicar
        </Button>
        <Button type="button" size="sm" variant="ghost" icon={<Trash weight="bold" />} onClick={onDelete}>
          Eliminar
        </Button>
      </div>
    </>
  );

  if (wide) {
    return (
      <aside ref={panel} aria-label="Propiedades del bloque" className="grid content-start gap-4 border-l border-line pl-6 lg:sticky lg:top-20">
        {body ?? (
          <>
            <Header title="Propiedades" />
            <p className="text-sm text-muted">Los títulos, párrafos y listas se escriben directo en el correo. Selecciona un botón, un evento o una imagen para ajustar sus detalles aquí.</p>
          </>
        )}
      </aside>
    );
  }
  if (!body) return null;
  return (
    <section
      ref={panel}
      aria-label="Propiedades del bloque"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          onClose();
        }
      }}
      className="fixed inset-x-0 bottom-0 z-40 grid max-h-[60dvh] content-start gap-4 overflow-y-auto rounded-t-3xl border-t border-line bg-surface p-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] shadow-lift"
    >
      <span aria-hidden className="mx-auto h-1.5 w-10 rounded-full bg-line" />
      {body}
    </section>
  );
}
