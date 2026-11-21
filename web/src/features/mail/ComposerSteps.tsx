// The composer's frame (spec 005 §Flow): a numbered stepper with a connecting line, and the footer with the step's
// one primary action. Steps are free to visit in any order, so every stepper item is a button.
import { ArrowLeft, ArrowRight, Check } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import { Button } from "@/components/Button";

import { STEPS, STEP_LABEL, type Step } from "./composerState";

export function Stepper({ step, onGo }: { step: Step; onGo: (next: Step) => void }) {
  const current = STEPS.indexOf(step);
  return (
    <nav aria-label="Pasos del correo" className="grid gap-3">
      <ol className="flex items-start">
        {STEPS.map((id, index) => {
          const done = index < current;
          const active = index === current;
          return (
            <li key={id} className={`flex items-start ${index < STEPS.length - 1 ? "flex-1" : ""}`}>
              <button
                type="button"
                aria-label={`Paso ${index + 1}: ${STEP_LABEL[id]}`}
                aria-current={active ? "step" : undefined}
                onClick={() => onGo(id)}
                className="group flex min-h-11 items-center gap-3 rounded-full pr-2 focus-visible:outline-3"
              >
                <span
                  aria-hidden
                  className={`grid size-9 shrink-0 place-items-center rounded-full border-2 text-sm font-bold transition duration-200 ${
                    active
                      ? "border-primary bg-primary text-on-primary shadow-soft"
                      : done
                        ? "border-primary bg-surface text-link"
                        : "border-line bg-surface text-muted group-hover:border-ink/30"
                  }`}
                >
                  {done ? <Check weight="bold" size={16} /> : index + 1}
                </span>
                <span aria-hidden className={`hidden text-sm font-semibold sm:inline ${active ? "text-ink" : "text-muted group-hover:text-ink"}`}>
                  {STEP_LABEL[id]}
                </span>
              </button>
              {index < STEPS.length - 1 && <span aria-hidden className={`mx-1 mt-[1.1rem] h-0.5 flex-1 rounded-full sm:mx-3 ${done ? "bg-primary" : "bg-line"}`} />}
            </li>
          );
        })}
      </ol>
      <p className="text-sm font-semibold sm:hidden" aria-hidden>
        {`Paso ${current + 1} de ${STEPS.length} · ${STEP_LABEL[step]}`}
      </p>
    </nav>
  );
}

/** Title block of a step: what to do here, in one line. */
export function StepHeader({ title, lead }: { title: string; lead: string }) {
  return (
    <header className="grid gap-1">
      <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-[1.7rem]">{title}</h2>
      <p className="max-w-prose text-muted">{lead}</p>
    </header>
  );
}

/** Back on the left, the step's single primary action on the right (full width stacked on phones). */
export function StepFooter({ onBack, children }: { onBack?: () => void; children: ReactNode }) {
  return (
    <div className="flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
      {onBack ? (
        <Button variant="ghost" icon={<ArrowLeft weight="bold" />} onClick={onBack} className="max-sm:w-full">
          Atrás
        </Button>
      ) : (
        <span />
      )}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">{children}</div>
    </div>
  );
}

export function NextButton({ onClick }: { onClick: () => void }) {
  return (
    <Button onClick={onClick} className="max-sm:w-full">
      Siguiente
      <ArrowRight weight="bold" />
    </Button>
  );
}
