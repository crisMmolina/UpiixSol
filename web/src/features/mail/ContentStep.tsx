// Step 2 · Contenido (spec 005 §Canvas): subject, preview text and the email canvas, where the sender edits on a
// picture of the email; "Ver como llega" opens the exact server render (desktop 600 / phone 375).
// This file also holds the DESIGN GATE mock `CanvasMock` (see its comment below): `/maqueta-correo` still mounts it
// from index.tsx, outside UPS-103's Paths, so it goes in a follow-up.
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  CalendarBlank,
  CopySimple,
  CursorClick,
  DotsSixVertical,
  Eye,
  Image as ImageIcon,
  LinkSimple,
  ListBullets,
  Minus,
  Plus,
  TextAlignLeft,
  TextB,
  TextHOne,
  TextItalic,
  Trash,
  X,
} from "@phosphor-icons/react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router";

import { LOGO_HEIGHT, useSite, Wordmark } from "@/lib/brand";
import { AcademyTheme, CAMPUS_BRANDING } from "@/lib/theme";

import { Button } from "@/components/Button";
import { TextField } from "@/components/Field";

import { MAX_PREHEADER, MAX_SUBJECT, type StepProps } from "./composerState";
import { NextButton, Stepper, StepFooter, StepHeader } from "./ComposerSteps";
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
      <StepHeader title="Escribe tu correo" lead="Haz clic en un bloque para editarlo y usa «+» para agregar más. Así se verá en la bandeja de entrada." />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Asunto" value={state.subject} maxLength={MAX_SUBJECT} onChange={(e) => dispatch({ type: "patch", patch: { subject: e.target.value.replace(/[\r\n]+/g, " ") } })} />
        <TextField
          label="Texto de vista previa (opcional)"
          value={state.preheader}
          maxLength={MAX_PREHEADER}
          hint="Lo que se ve junto al asunto en la bandeja de entrada."
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

// DESIGN GATE mock (UPS-102, spec 005 §Canvas): a STATIC picture of how step 2 will look once UPS-103 lets the sender
// edit on the email. Nothing here saves or sends. `?estado=texto|boton|insertar` picks the state shown:
//   texto    a text block selected, with its inline toolbar
//   boton    a button block selected, properties in a side panel (desktop) or a bottom sheet (phones)
//   insertar the "+" inserter open between two blocks
// UPS-103 removes this mock when the real canvas replaces it.
type Estado = "texto" | "boton" | "insertar";
const ESTADOS: { id: Estado; label: string }[] = [
  { id: "texto", label: "Texto" },
  { id: "boton", label: "Botón" },
  { id: "insertar", label: "Insertar" },
];

const KINDS = [
  { icon: TextHOne, name: "Título", hint: "Un encabezado grande" },
  { icon: TextAlignLeft, name: "Párrafo", hint: "Texto con negritas y enlaces" },
  { icon: ListBullets, name: "Lista", hint: "Con viñetas o numerada" },
  { icon: CursorClick, name: "Botón", hint: "Un enlace destacado" },
  { icon: CalendarBlank, name: "Evento", hint: "Tarjeta con fecha y calendario" },
  { icon: ImageIcon, name: "Imagen", hint: "Sube un cartel o una foto" },
  { icon: Minus, name: "Separador", hint: "Una línea para respirar" },
];

const tool = "grid size-9 place-items-center rounded-lg text-surface transition hover:bg-surface/15 focus-visible:outline-3";

function Toolbar() {
  return (
    <div role="toolbar" aria-label="Formato del texto" className="absolute -top-12 left-2 z-10 flex items-center gap-0.5 rounded-xl bg-ink p-1 shadow-lift">
      <button type="button" className={tool} aria-label="Negritas"><TextB weight="bold" size={18} /></button>
      <button type="button" className={tool} aria-label="Cursivas"><TextItalic weight="bold" size={18} /></button>
      <button type="button" className={tool} aria-label="Enlace"><LinkSimple weight="bold" size={18} /></button>
      <span aria-hidden className="mx-1 h-5 w-px bg-surface/25" />
      <button type="button" className={tool} aria-label="Subir bloque"><ArrowUp weight="bold" size={18} /></button>
      <button type="button" className={tool} aria-label="Bajar bloque"><ArrowDown weight="bold" size={18} /></button>
      <button type="button" className={tool} aria-label="Duplicar bloque"><CopySimple weight="bold" size={18} /></button>
      <button type="button" className={tool} aria-label="Eliminar bloque"><Trash weight="bold" size={18} /></button>
    </div>
  );
}

function Block({ label, selected, toolbar, children }: { label: string; selected?: boolean; toolbar?: boolean; children: ReactNode }) {
  return (
    <div className={`group relative rounded-lg px-3 py-2 transition ${selected ? "ring-2 ring-primary" : "hover:ring-1 hover:ring-line"} ${selected && toolbar ? "mt-14" : ""}`}>
      {selected && toolbar && <Toolbar />}
      {selected && (
        <>
          <span className="absolute -bottom-3 right-2 rounded-full bg-primary px-2.5 py-0.5 text-xs font-bold text-on-primary">{label}</span>
          <span aria-hidden className="absolute top-1/2 -left-6 hidden -translate-y-1/2 cursor-grab text-muted sm:block">
            <DotsSixVertical weight="bold" size={20} />
          </span>
        </>
      )}
      {children}
    </div>
  );
}

function Inserter({ open }: { open: boolean }) {
  return (
    <div className="relative my-1 flex h-7 items-center">
      <span aria-hidden className={`h-px flex-1 ${open ? "bg-primary" : "bg-line"}`} />
      <button
        type="button"
        aria-label="Insertar bloque aquí"
        aria-expanded={open}
        className={`mx-2 grid size-7 place-items-center rounded-full border-2 transition focus-visible:outline-3 ${open ? "border-primary bg-primary text-on-primary" : "border-line bg-surface text-muted hover:border-primary hover:text-ink"}`}
      >
        <Plus weight="bold" size={14} />
      </button>
      <span aria-hidden className={`h-px flex-1 ${open ? "bg-primary" : "bg-line"}`} />
      {open && (
        <div role="menu" aria-label="Tipo de bloque" className="absolute top-9 left-1/2 z-20 w-[min(19rem,100%)] -translate-x-1/2 rounded-2xl border border-line bg-surface p-2 shadow-lift">
          {KINDS.map(({ icon: Icon, name, hint }) => (
            <button key={name} type="button" role="menuitem" className="flex w-full items-center gap-3 rounded-xl px-2 py-1.5 text-left hover:bg-subtle focus-visible:outline-3">
              <span aria-hidden className="grid size-9 shrink-0 place-items-center rounded-lg bg-subtle text-ink">
                <Icon weight="bold" size={18} />
              </span>
              <span className="grid min-w-0">
                <span className="text-sm font-semibold">{name}</span>
                <span className="truncate text-xs text-muted">{hint}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ButtonFields() {
  return (
    <div className="grid gap-4">
      <TextField label="Texto del botón" defaultValue="Ir al campus" />
      <TextField label="Enlace del botón" defaultValue="https://www.upiixsol.com/" />
      <div className="flex flex-wrap gap-2" role="group" aria-label="Enlaces rápidos">
        <Button size="sm" variant="secondary">Ir al campus</Button>
        <Button size="sm" variant="secondary">Ver el club</Button>
      </div>
      <div className="flex gap-2 border-t border-line pt-4">
        <Button size="sm" variant="secondary" icon={<CopySimple weight="bold" />}>Duplicar</Button>
        <Button size="sm" variant="ghost" icon={<Trash weight="bold" />}>Eliminar</Button>
      </div>
    </div>
  );
}

function PanelHeader({ title, onClose }: { title: string; onClose?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <h3 className="font-display text-lg font-semibold">{title}</h3>
      {onClose && (
        <button type="button" aria-label="Cerrar propiedades" className="grid size-11 place-items-center rounded-full hover:bg-subtle focus-visible:outline-3">
          <X weight="bold" />
        </button>
      )}
    </div>
  );
}

function CanvasMockScreen() {
  const site = useSite();
  const [search, setSearch] = useSearchParams();
  const estado: Estado = ESTADOS.find((e) => e.id === search.get("estado"))?.id ?? "texto";
  return (
    <main className="mx-auto grid max-w-6xl gap-6 px-4 pt-6 pb-40 sm:px-6 sm:pt-10 lg:pb-12">
      <p className="rounded-xl border border-dashed border-line bg-subtle px-4 py-2 text-sm text-muted">
        <span className="font-semibold text-ink">Maqueta estática.</span> Así se verá editar sobre el correo; todavía no guarda ni envía.
      </p>
      <div role="group" aria-label="Estado de la maqueta" className="flex w-full gap-1 rounded-full border border-line p-0.5 sm:w-fit">
        {ESTADOS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            aria-pressed={estado === id}
            onClick={() => setSearch({ estado: id }, { replace: true })}
            className={`min-h-11 flex-1 rounded-full px-4 text-sm font-semibold whitespace-nowrap focus-visible:outline-3 ${estado === id ? "bg-ink text-surface" : "text-ink hover:bg-subtle"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <div>
        <div className="grid gap-7">
          <Stepper step="contenido" onGo={() => undefined} />
          <header className="grid gap-1">
            <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-[1.7rem]">Escribe tu correo</h2>
            <p className="hidden max-w-prose text-muted sm:block">Haz clic en un bloque para editarlo. Usa «+» para agregar más.</p>
          </header>
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_19rem]">
            <div className="rounded-2xl bg-subtle px-3 py-8 sm:px-8">
              <div className="mx-auto w-full max-w-[600px] rounded-2xl border border-line bg-surface px-4 py-6 shadow-soft sm:px-8">
                <div className="mb-6 grid gap-1 border-b border-line pb-5">
                  {site.logoUrl ? (
                    <img src={site.logoUrl} alt={site.name} {...site.logoSize} className={`h-(--logo-h) w-auto ${LOGO_HEIGHT.login}`} />
                  ) : (
                    <Wordmark
                      name={site.name}
                      colors={{ color_primary: site.colors.primary, color_secondary: site.colors.secondary, color_accent: site.colors.accent }}
                      className={`block max-w-full break-words ${LOGO_HEIGHT.login}`}
                    />
                  )}
                  <p className="text-xs text-muted">Enviado por La mesa directiva de UpiixSol</p>
                </div>
                <div className="grid gap-1">
                  <Block label="Título" selected={estado === "texto"} toolbar>
                    <h3 className="font-display text-2xl leading-tight font-semibold">Escribe aquí el título</h3>
                  </Block>
                  <Inserter open={estado === "insertar"} />
                  <Block label="Párrafo">
                    <p className="leading-relaxed">
                      Cuenta lo importante en dos o tres líneas. Puedes poner <strong>negritas</strong>, <em>cursivas</em> y{" "}
                      <span className="text-link underline">enlaces</span>.
                    </p>
                  </Block>
                  <Inserter open={false} />
                  <Block label="Botón" selected={estado === "boton"}>
                    <span className="inline-flex min-h-11 items-center rounded-full bg-primary px-6 font-semibold text-on-primary">Ir al campus</span>
                  </Block>
                  <Inserter open={false} />
                </div>
                <p className="mt-4 border-t border-line pt-4 text-xs text-muted">Recibes este correo por ser parte de UpiixSol · Darme de baja</p>
              </div>
            </div>
            <aside aria-label="Propiedades del bloque" className="hidden content-start gap-4 border-l border-line pl-6 lg:grid lg:sticky lg:top-20">
              {estado === "boton" ? (
                <>
                  <PanelHeader title="Botón" onClose />
                  <ButtonFields />
                </>
              ) : (
                <>
                  <PanelHeader title="Propiedades" />
                  <p className="text-sm text-muted">Los títulos, párrafos y listas se escriben directo en el correo. Selecciona un botón, un evento o una imagen para ajustar sus detalles aquí.</p>
                </>
              )}
            </aside>
          </div>
          <div className="flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
            <Button variant="ghost" icon={<ArrowLeft weight="bold" />} className="max-sm:w-full">Atrás</Button>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button variant="secondary" className="max-sm:w-full">Ver como llega</Button>
              <Button className="max-sm:w-full">Siguiente<ArrowRight weight="bold" /></Button>
            </div>
          </div>
        </div>
      </div>
      {estado === "boton" && (
        <section aria-label="Propiedades del bloque" className="fixed inset-x-0 bottom-0 z-30 grid gap-4 rounded-t-3xl border-t border-line bg-surface p-5 pb-6 shadow-lift lg:hidden">
          <span aria-hidden className="mx-auto h-1.5 w-10 rounded-full bg-line" />
          <PanelHeader title="Botón" onClose />
          <ButtonFields />
        </section>
      )}
    </main>
  );
}

export function CanvasMock() {
  return (
    <AcademyTheme branding={CAMPUS_BRANDING}>
      <CanvasMockScreen />
    </AcademyTheme>
  );
}
