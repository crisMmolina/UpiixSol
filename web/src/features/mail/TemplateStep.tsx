// Step 1 · Plantilla. For now only "En blanco"; the gallery of built-in and saved templates arrives with UPS-104.
import { Check } from "@phosphor-icons/react";

import { NextButton, StepFooter, StepHeader } from "./ComposerSteps";

/** A small wireframe of an email: header bar, a title line, a few text lines and a button. */
function BlankThumb() {
  return (
    <span aria-hidden className="grid h-full content-start gap-3 rounded-2xl border border-line bg-surface p-5 shadow-soft">
      <span className="h-1.5 w-full rounded-full bg-primary" />
      <span className="mx-auto mt-2 h-4 w-24 rounded-full bg-primary/60" />
      <span className="mt-3 h-4 w-3/4 rounded-full bg-line" />
      <span className="h-2.5 w-full rounded-full bg-subtle" />
      <span className="h-2.5 w-11/12 rounded-full bg-subtle" />
      <span className="h-2.5 w-2/3 rounded-full bg-subtle" />
      <span className="mt-2 h-8 w-28 rounded-full border-2 border-dashed border-line" />
    </span>
  );
}

export function TemplateStep({ onNext }: { onNext: () => void }) {
  return (
    <div className="grid gap-7">
      <StepHeader title="¿Cómo quieres empezar?" lead="Elige un punto de partida; en el siguiente paso cambias todo lo que quieras. Pronto habrá plantillas listas para anuncios, eventos y recordatorios." />
      <button
        type="button"
        aria-pressed
        className="relative grid w-full items-center gap-6 rounded-3xl border-2 border-primary bg-subtle p-4 text-left transition duration-200 hover:shadow-lift focus-visible:outline-3 sm:grid-cols-[minmax(0,20rem)_1fr] sm:gap-10 sm:p-6"
      >
        <span className="block h-56 sm:h-64">
          <BlankThumb />
        </span>
        <span className="grid gap-2 sm:pr-10">
          <span className="font-display text-xl font-semibold">En blanco</span>
          <span className="max-w-prose text-muted">Empieza con un párrafo vacío y arma tu correo con títulos, botones, eventos e imágenes.</span>
        </span>
        <span aria-hidden className="absolute top-4 right-4 grid size-7 place-items-center rounded-full bg-primary text-on-primary">
          <Check weight="bold" size={16} />
        </span>
      </button>
      <StepFooter>
        <NextButton onClick={onNext} />
      </StepFooter>
    </div>
  );
}
