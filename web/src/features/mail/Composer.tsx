// Composer (spec 003): audience, subject, plain-text body, test send, and the review-and-confirm modal.
import { PaperPlaneTilt } from "@phosphor-icons/react";
import { useState } from "react";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextArea, TextField } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Modal } from "@/components/Overlay";
import { Notice } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import type { AudiencePreview, Campaign, MailStatus } from "@/lib/types";

import { AudiencePicker, EMPTY_AUDIENCE, toAudience, type AcademyChoice, type AudienceDraft, type AudienceKind } from "./AudiencePicker";

const MAX_BODY = 20_000;
const MAX_SUBJECT = 150;

function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

function ConfirmBody({ preview, status }: { preview: AudiencePreview; status: MailStatus }) {
  const { excluded } = preview;
  const skipped = [
    excluded.inactive > 0 && plural(excluded.inactive, "cuenta inactiva", "cuentas inactivas"),
    excluded.suppressed > 0 && plural(excluded.suppressed, "persona dada de baja", "personas dadas de baja"),
    excluded.blocked_domain > 0 && plural(excluded.blocked_domain, "correo de dominio no válido", "correos de dominio no válido"),
  ].filter(Boolean);
  return (
    <div className="grid gap-3">
      <p className="text-lg font-semibold">{`Se enviará a ${plural(preview.count, "persona", "personas")}`}</p>
      {skipped.length > 0 && <p className="text-sm text-muted">{`No se incluyen: ${skipped.join(", ")}.`}</p>}
      <p className="text-sm text-muted">{`Hoy puedes enviar ${plural(status.remaining, "correo", "correos")} más (límite diario: ${status.daily_limit}).`}</p>
    </div>
  );
}

export function Composer({
  status,
  academies,
  kinds,
  ownClub,
  onSent,
}: {
  status: MailStatus;
  academies: AcademyChoice[];
  kinds?: AudienceKind[];
  ownClub?: boolean;
  onSent: (campaign: Campaign) => void;
}) {
  const [draft, setDraft] = useState<AudienceDraft>({ ...EMPTY_AUDIENCE, kind: kinds?.[0] ?? "all", academyId: ownClub ? (academies[0]?.id ?? null) : null });
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [testNote, setTestNote] = useState<{ text: string; tone: "error" | "success" } | null>(null);
  const [testing, setTesting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [preview, setPreview] = useState<AudiencePreview | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sentNote, setSentNote] = useState<string | null>(null);

  const audience = toAudience(draft);
  const ready = subject.trim().length > 0 && body.trim().length > 0;
  const off = !status.enabled;

  async function sendTest() {
    setSentNote(null);
    if (!ready) return setTestNote({ text: "Escribe un asunto y un mensaje para enviar la prueba.", tone: "error" });
    setTesting(true);
    try {
      await api("/mail/test", { method: "POST", json: { subject: subject.trim(), body } });
      setTestNote({ text: "Prueba enviada a tu correo.", tone: "success" });
    } catch (err) {
      setTestNote({ text: errorMessage(err), tone: "error" });
    } finally {
      setTesting(false);
    }
  }

  async function review() {
    setTestNote(null);
    setSentNote(null);
    if (!ready) return setFormError("Escribe un asunto y un mensaje.");
    if (!audience) return setFormError("Elige a quién enviar el correo.");
    setFormError(null);
    setChecking(true);
    try {
      setPreview(await api<AudiencePreview>("/mail/audience/preview", { method: "POST", json: audience }));
      setSendError(null);
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setChecking(false);
    }
  }

  async function confirm() {
    if (!audience || sending) return;
    setSending(true);
    setSendError(null);
    try {
      const created = await api<Campaign>("/mail/campaigns", { method: "POST", json: { subject: subject.trim(), body, audience } });
      const campaign = await api<Campaign>(`/mail/campaigns/${created.id}/send`, { method: "POST" });
      setPreview(null);
      setSubject("");
      setBody("");
      setDraft({ ...EMPTY_AUDIENCE, kind: draft.kind, academyId: draft.academyId });
      setSentNote("El envío está en curso. Sigue su avance en el historial.");
      onSent(campaign);
    } catch (err) {
      setSendError(errorMessage(err));
    } finally {
      setSending(false);
    }
  }

  const tooMany = preview !== null && preview.count > status.remaining;
  const confirmHint = preview === null ? null : preview.count === 0 ? "Nadie recibiría este correo: cambia los destinatarios." : tooMany ? `Supera tu cupo de hoy (${status.remaining}).` : null;

  return (
    <Card className="grid gap-5 p-5 sm:p-6">
      {off && <Notice tone="alert">El correo está desactivado. Puedes redactar, pero no enviar, hasta que se active.</Notice>}
      <AudiencePicker draft={draft} onChange={setDraft} academies={academies} kinds={kinds} ownClub={ownClub} />
      <TextField label="Asunto" value={subject} maxLength={MAX_SUBJECT} onChange={(e) => setSubject(e.target.value.replace(/[\r\n]+/g, " "))} />
      <div className="grid gap-1">
        <TextArea label="Mensaje" value={body} maxLength={MAX_BODY} rows={8} onChange={(e) => setBody(e.target.value)} hint="Texto sin formato: las líneas en blanco separan párrafos y los enlaces https se vuelven clicables." />
        <p className="text-right text-xs tabular-nums text-muted">{`${body.length.toLocaleString("es-MX")} / ${MAX_BODY.toLocaleString("es-MX")}`}</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" variant="secondary" onClick={() => void sendTest()} disabled={off} loading={testing}>
          Enviarme una prueba
        </Button>
        <Button type="button" icon={<PaperPlaneTilt weight="bold" />} onClick={() => void review()} disabled={off} loading={checking}>
          Revisar y enviar
        </Button>
      </div>
      <FormMessage message={formError ?? testNote?.text} tone={formError ? "error" : (testNote?.tone ?? "error")} />
      {sentNote && <p role="status" className="text-sm font-semibold text-link">{sentNote}</p>}

      <Modal open={preview !== null} onClose={() => !sending && setPreview(null)} title="Revisar envío">
        {preview && (
          <div className="grid gap-4">
            <ConfirmBody preview={preview} status={status} />
            <p className="truncate text-sm">
              <span className="text-muted">Asunto: </span>
              {subject}
            </p>
            <FormMessage message={sendError} hint={confirmHint} lines={2} />
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="ghost" onClick={() => setPreview(null)} disabled={sending}>
                Cancelar
              </Button>
              <Button onClick={() => void confirm()} loading={sending} disabled={sending || preview.count === 0 || tooMany}>
                Enviar ahora
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </Card>
  );
}
