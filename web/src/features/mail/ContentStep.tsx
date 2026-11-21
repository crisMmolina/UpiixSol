// Step 2 · Contenido (spec 005 §Canvas): subject, preview text and the email canvas, where the sender edits on a
// picture of the email; "Ver como llega" opens the exact server render (desktop 600 / phone 375).
import { BookmarkSimple, Eye, X } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/Button";
import { TextField } from "@/components/Field";
import type { Block } from "@/lib/types";

import { toBlock } from "./blocks";
import { contentSignature, MAX_PREHEADER, MAX_TEMPLATE_NAME, MAX_SUBJECT, type StepProps } from "./composerState";
import { NextButton, StepFooter, StepHeader } from "./ComposerSteps";
import { EmailCanvas } from "./EmailCanvas";
import { EmailPreview } from "./EmailPreview";
import { createTemplate, TemplateNameDialog } from "./SaveTemplateDialog";

/** The exact server render in a native modal dialog (focus trap, Esc), wide enough for the 600 px email. */
function SeeAsSent({ open, onClose, payload }: { open: boolean; onClose: () => void; payload: object | null }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      data-keep-selection
      aria-label="Así llega el correo"
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
      className="m-auto max-h-[calc(100dvh-2rem)] w-[min(42rem,calc(100vw-2rem))] rounded-card bg-surface p-0 text-ink shadow-lift backdrop:bg-ink/40"
    >
      {open && (
        <div className="grid gap-4 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg">Así llega el correo</h2>
            <button type="button" onClick={onClose} aria-label="Cerrar" className="grid size-11 place-items-center rounded-full hover:bg-subtle focus-visible:outline-3">
              <X weight="bold" />
            </button>
          </div>
          <EmailPreview payload={payload} emptyHint="Agrega contenido para ver cómo queda el correo." />
        </div>
      )}
    </dialog>
  );
}

/** What a template keeps: the complete blocks, plus the event slot ("Completa el evento") when the event is still empty. */
function templateBlocks(state: StepProps["state"]): Block[] {
  return state.drafts.flatMap((draft): Block[] => {
    const block = toBlock(draft);
    if (block) return [block];
    return draft.kind === "event" && draft.mode === "campus" && draft.eventId === null ? [{ kind: "event", placeholder: true }] : [];
  });
}

export function ContentStep({ state, dispatch, clubSlug, eventsAcademy, previewPayload, ownClub, onBack, onNext }: StepProps & { ownClub: boolean; onNext: () => void }) {
  const [seeing, setSeeing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  return (
    <div className="grid gap-7">
      <StepHeader title="Escribe tu correo" lead="Haz clic en un bloque para editarlo; «+» agrega más." />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Asunto" value={state.subject} maxLength={MAX_SUBJECT} onChange={(e) => dispatch({ type: "patch", patch: { subject: e.target.value.replace(/[\r\n]+/g, " ") } })} />
        <TextField
          label="Texto de vista previa (opcional)"
          value={state.preheader}
          maxLength={MAX_PREHEADER}
          placeholder="Se ve junto al asunto en la bandeja de entrada"
          onChange={(e) => dispatch({ type: "patch", patch: { preheader: e.target.value.replace(/[\r\n]+/g, " ") } })}
        />
      </div>
      <EmailCanvas drafts={state.drafts} onChange={(drafts) => dispatch({ type: "patch", patch: { drafts } })} clubSlug={clubSlug} eventsAcademy={eventsAcademy} previewPayload={previewPayload} />
      <StepFooter onBack={onBack}>
        <Button variant="secondary" icon={<BookmarkSimple weight="bold" />} onClick={() => { setSaved(null); setSaving(true); }} className="max-sm:w-full" data-keep-selection>
          Guardar como plantilla
        </Button>
        <Button variant="secondary" icon={<Eye weight="bold" />} onClick={() => setSeeing(true)} className="max-sm:w-full" data-keep-selection>
          Ver como llega
        </Button>
        <NextButton onClick={onNext} />
      </StepFooter>
      {saved && (
        <p role="status" className="text-sm font-semibold text-link">
          {saved}
        </p>
      )}
      <TemplateNameDialog
        open={saving}
        mode="save"
        where={ownClub ? "tu club" : "UpiixSol"}
        initial={{ name: state.templateName ?? state.subject.trim().slice(0, MAX_TEMPLATE_NAME), description: "" }}
        onClose={() => setSaving(false)}
        onSubmit={async (name, description) => {
          const blocks = templateBlocks(state);
          if (!state.subject.trim() || blocks.length === 0) throw new Error("Escribe un asunto y al menos un bloque antes de guardar la plantilla.");
          const created = await createTemplate(name, description, { subject: state.subject.trim(), preheader: state.preheader.trim() || undefined, blocks });
          dispatch({ type: "patch", patch: { template: { id: created.id, sig: contentSignature(state) } } });
          setSaved("Plantilla guardada. La encuentras en el primer paso.");
        }}
      />
      <SeeAsSent open={seeing} onClose={() => setSeeing(false)} payload={previewPayload} />
    </div>
  );
}
