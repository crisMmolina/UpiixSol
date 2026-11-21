// Step 3 · Destinatarios y envío: audience, who it is sent as, Reply-To, the month's quota and the one action.
import { PaperPlaneTilt } from "@phosphor-icons/react";
import type { ReactNode } from "react";

import { Button } from "@/components/Button";
import { SelectField } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Notice } from "@/components/States";
import type { MailStatus } from "@/lib/types";

import { AudiencePicker, type AcademyChoice, type AudienceKind } from "./AudiencePicker";
import { BOARD, renewal, type StepProps } from "./composerState";
import { StepFooter, StepHeader } from "./ComposerSteps";
import { EmailPreview } from "./EmailPreview";
import { ReplyToField } from "./ReplyToField";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-3">
      <h3 className="font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function Quota({ status }: { status: MailStatus }) {
  const used = Math.min(100, Math.round((status.sent_this_period / Math.max(1, status.monthly_limit)) * 100));
  return (
    <div className="grid gap-2 rounded-2xl bg-subtle p-4">
      <p className="text-sm">{`Te quedan ${status.remaining.toLocaleString("en-US")} de ${status.monthly_limit.toLocaleString("en-US")} correos este mes · se renueva el ${renewal(status.period_end)}`}</p>
      <div aria-hidden className="h-1.5 overflow-hidden rounded-full bg-line">
        <div className="h-full rounded-full bg-primary" style={{ width: `${used}%` }} />
      </div>
    </div>
  );
}

export function SendStep({
  state,
  dispatch,
  previewPayload,
  onBack,
  status,
  academies,
  kinds,
  ownClub,
  senderId,
  audienceClub,
  formError,
  checking,
  onReview,
}: StepProps & {
  status: MailStatus;
  academies: AcademyChoice[];
  kinds?: AudienceKind[];
  ownClub?: boolean;
  senderId: number | null;
  audienceClub: number | null;
  formError: string | null;
  checking: boolean;
  onReview: () => void;
}) {
  const off = !status.enabled;
  return (
    <div className="grid gap-7">
      <StepHeader title="¿A quién se lo mandas?" lead="Elige los destinatarios, revisa quién lo envía y confirma. Antes de enviar verás cuántas personas lo reciben." />
      {off && <Notice tone="alert">El correo está desactivado. Puedes redactar, pero no enviar, hasta que se active.</Notice>}
      <div className="grid items-start gap-8 lg:grid-cols-2">
        <div className="grid min-w-0 content-start gap-7">
          <AudiencePicker draft={state.audience} onChange={(audience) => dispatch({ type: "patch", patch: { audience, sender: "auto" } })} academies={academies} kinds={kinds} ownClub={ownClub} />
          <Section title="Quién lo envía">
            {ownClub ? (
              <p className="text-sm">{`Enviado por ${academies[0]?.name ?? ""}`}</p>
            ) : (
              <SelectField label="Enviado por" value={senderId ?? ""} onChange={(e) => dispatch({ type: "patch", patch: { sender: e.target.value ? Number(e.target.value) : null } })}>
                <option value="" disabled={audienceClub !== null}>
                  {BOARD}
                </option>
                {academies.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </SelectField>
            )}
            <ReplyToField value={state.replyTo} onChange={(replyTo) => dispatch({ type: "patch", patch: { replyTo } })} />
          </Section>
          <Quota status={status} />
        </div>
        <div className="min-w-0 lg:sticky lg:top-20">
          <EmailPreview payload={previewPayload} emptyHint="Agrega contenido para ver cómo queda el correo." />
        </div>
      </div>
      <StepFooter onBack={onBack}>
        <Button icon={<PaperPlaneTilt weight="bold" />} onClick={onReview} disabled={off} loading={checking} className="max-sm:w-full">
          Revisar y enviar
        </Button>
      </StepFooter>
      <FormMessage message={formError} tone="error" />
    </div>
  );
}
