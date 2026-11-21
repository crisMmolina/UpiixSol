// Step 2 · Contenido: subject, preview text and the blocks, with the exact server preview beside them.
// UPS-103 replaces the block editor with the email canvas; the step's frame stays.
import { TextField } from "@/components/Field";

import { BlockEditor } from "./BlockEditor";
import { MAX_PREHEADER, MAX_SUBJECT, type StepProps } from "./composerShared";
import { NextButton, StepFooter, StepHeader } from "./ComposerSteps";
import { EmailPreview } from "./EmailPreview";

export function ContentStep({ state, dispatch, clubSlug, eventsAcademy, previewPayload, onBack, onNext }: StepProps & { onNext: () => void }) {
  return (
    <div className="grid gap-7">
      <StepHeader title="Escribe tu correo" lead="Asunto, texto de vista previa y los bloques del mensaje. A la derecha ves cómo llega." />
      <div className="grid items-start gap-8 lg:grid-cols-2">
        <div className="grid min-w-0 content-start gap-6">
          <div className="grid gap-4">
            <TextField label="Asunto" value={state.subject} maxLength={MAX_SUBJECT} onChange={(e) => dispatch({ type: "patch", patch: { subject: e.target.value.replace(/[\r\n]+/g, " ") } })} />
            <TextField
              label="Texto de vista previa (opcional)"
              value={state.preheader}
              maxLength={MAX_PREHEADER}
              hint="Lo que se ve junto al asunto en la bandeja de entrada."
              onChange={(e) => dispatch({ type: "patch", patch: { preheader: e.target.value.replace(/[\r\n]+/g, " ") } })}
            />
          </div>
          <BlockEditor drafts={state.drafts} onChange={(drafts) => dispatch({ type: "patch", patch: { drafts } })} clubSlug={clubSlug} eventsAcademy={eventsAcademy} />
        </div>
        <div className="min-w-0 lg:sticky lg:top-20">
          <EmailPreview payload={previewPayload} emptyHint="Agrega contenido para ver cómo queda el correo." />
        </div>
      </div>
      <StepFooter onBack={onBack}>
        <NextButton onClick={onNext} />
      </StepFooter>
    </div>
  );
}
