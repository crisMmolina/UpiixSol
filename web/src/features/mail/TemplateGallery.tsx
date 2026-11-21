// The gallery of step 1: cards with a live thumbnail, name and description, grouped by who owns them.
import { Check, PencilSimple, TrashSimple } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import type { MailTemplate } from "@/lib/types";

import { TemplateThumbnail, Wireframe } from "./TemplateThumbnail";

const action = "grid size-11 place-items-center rounded-full bg-surface/90 text-ink shadow-soft hover:bg-subtle focus-visible:outline-3";

function Card({ selected, onPick, thumb, name, description, children }: { selected: boolean; onPick: () => void; thumb: ReactNode; name: string; description: string | null; children?: ReactNode }) {
  return (
    <li className="relative">
      <button
        type="button"
        onClick={onPick}
        aria-pressed={selected}
        className={`grid h-full w-full content-start gap-3 rounded-2xl border-2 p-2.5 text-left sm:rounded-3xl sm:p-3 transition duration-200 hover:shadow-lift focus-visible:outline-3 ${selected ? "border-primary bg-subtle" : "border-line bg-surface"}`}
      >
        <span aria-hidden className="block">
          {thumb}
        </span>
        <span className="grid gap-1 px-1 pb-1 [&>span:last-child]:line-clamp-3">
          <span className="font-display text-base leading-tight font-semibold sm:text-lg">{name}</span>
          {description && <span className="text-sm text-muted">{description}</span>}
        </span>
        {selected && (
          <span aria-hidden className="absolute top-4 left-4 grid size-7 place-items-center rounded-full bg-primary text-on-primary">
            <Check weight="bold" size={16} />
          </span>
        )}
      </button>
      {children}
    </li>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const id = `gallery-${title.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <section aria-labelledby={id} className="grid gap-3">
      <h3 id={id} className="font-display text-lg font-semibold">
        {title}
      </h3>
      <ul className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">{children}</ul>
    </section>
  );
}

export function TemplateGallery({
  templates,
  blank,
  selected,
  ownClub,
  onPick,
  onBlank,
  onRename,
  onDelete,
}: {
  templates: MailTemplate[];
  blank: boolean;
  selected: string | number | null;
  ownClub: boolean;
  onPick: (template: MailTemplate) => void;
  onBlank: () => void;
  onRename: (template: MailTemplate) => void;
  onDelete: (template: MailTemplate) => void;
}) {
  const site = templates.filter((t) => t.scope === "site");
  const clubs = templates.filter((t) => t.scope === "academy");
  /** Mine to edit: UpiixSol's for a superadmin, my club's for a club admin. Built-ins never. */
  const mine = (t: MailTemplate) => t.kind === "saved" && (ownClub ? t.scope === "academy" : t.scope === "site");
  const card = (t: MailTemplate) => (
    <Card key={t.id} selected={selected === t.id} onPick={() => onPick(t)} thumb={<TemplateThumbnail name={t.name} subject={t.subject} preheader={t.preheader} blocks={t.blocks} />} name={t.name} description={t.description}>
      {mine(t) && (
        <div className="absolute top-4 right-4 flex gap-1.5">
          <button type="button" aria-label={`Renombrar ${t.name}`} title="Renombrar" onClick={() => onRename(t)} className={action}>
            <PencilSimple weight="bold" aria-hidden />
          </button>
          <button type="button" aria-label={`Eliminar ${t.name}`} title="Eliminar" onClick={() => onDelete(t)} className={action}>
            <TrashSimple weight="bold" aria-hidden />
          </button>
        </div>
      )}
    </Card>
  );
  return (
    <div className="grid gap-7">
      {site.length > 0 && <Section title="Plantillas de UpiixSol">{site.map(card)}</Section>}
      {clubs.length > 0 && <Section title={ownClub ? "Plantillas de mi club" : "Plantillas de clubes"}>{clubs.map(card)}</Section>}
      <Section title="En blanco">
        <Card selected={blank} onPick={onBlank} thumb={<span className="block aspect-[3/4]"><Wireframe /></span>} name="En blanco" description="Empieza con un párrafo vacío y arma tu correo con títulos, botones, eventos e imágenes." />
      </Section>
    </div>
  );
}
