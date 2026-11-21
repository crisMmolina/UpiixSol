// Step 1 · Plantilla. For now only "En blanco"; the gallery of built-in and saved templates arrives with UPS-104.
import { Check } from "@phosphor-icons/react";

import { NextButton, StepFooter, StepHeader } from "./ComposerSteps";

/** A small wireframe of an email: header bar, a title line, a few text lines and a button. */
function BlankThumb() {
  return (
    <span aria-hidden className="grid h-full content-start gap-2 rounded-xl border border-line bg-surface p-3">
      <span className="h-2 w-10 rounded-full bg-primary/70" />
      <span className="mt-1 h-3 w-3/4 rounded-full bg-line" />
      <span className="h-2 w-full rounded-full bg-subtle" />
      <span className="h-2 w-5/6 rounded-full bg-subtle" />
      <span className="mt-1 h-5 w-16 rounded-full border border-dashed border-line" />
    </span>
  );
}

export function TemplateStep({ onNext }: { onNext: () => void }) {
  return (
    <div className="grid gap-7">
      <StepHeader title="¿Cómo quieres empezar?" lead="Elige un punto de partida. Podrás cambiar todo en el siguiente paso." />
      <ul className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(10.5rem,1fr))]">
        <li>
          <button
            type="button"
            aria-pressed
            className="group relative grid h-full w-full gap-3 rounded-2xl border-2 border-primary bg-subtle p-3 text-left shadow-soft transition duration-200 hover:shadow-lift focus-visible:outline-3"
          >
            <span className="block h-36">
              <BlankThumb />
            </span>
            <span className="grid gap-0.5 px-1 pb-1">
              <span className="font-semibold">En blanco</span>
              <span className="text-sm text-muted">Un párrafo vacío para empezar de cero.</span>
            </span>
            <span aria-hidden className="absolute top-5 right-5 grid size-6 place-items-center rounded-full bg-primary text-on-primary">
              <Check weight="bold" size={14} />
            </span>
          </button>
        </li>
      </ul>
      <p className="text-sm text-muted">Muy pronto: plantillas listas para anuncios, eventos y recordatorios, y las tuyas guardadas.</p>
      <StepFooter>
        <NextButton onClick={onNext} />
      </StepFooter>
    </div>
  );
}
