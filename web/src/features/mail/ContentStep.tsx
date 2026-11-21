// Step 2 · Contenido (spec 005 §Canvas): subject, preview text and the email canvas, where the sender edits on a
// picture of the email; "Ver como llega" opens the exact server render (desktop 600 / phone 375).
import { Eye, X } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/Button";
import { TextField } from "@/components/Field";

import { MAX_PREHEADER, MAX_SUBJECT, type StepProps } from "./composerState";
import { NextButton, StepFooter, StepHeader } from "./ComposerSteps";
import { EmailCanvas } from "./EmailCanvas";
import { EmailPreview } from "./EmailPreview";

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

export function ContentStep({ state, dispatch, clubSlug, eventsAcademy, previewPayload, onBack, onNext }: StepProps & { onNext: () => void }) {
  const [seeing, setSeeing] = useState(false);
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
        <Button variant="secondary" icon={<Eye weight="bold" />} onClick={() => setSeeing(true)} className="max-sm:w-full" data-keep-selection>
          Ver como llega
        </Button>
        <NextButton onClick={onNext} />
      </StepFooter>
      <SeeAsSent open={seeing} onClose={() => setSeeing(false)} payload={previewPayload} />
    </div>
  );
}
