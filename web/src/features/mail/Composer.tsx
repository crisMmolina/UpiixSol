// Composer (specs 003, 004): audience, sender, subject, block editor with live preview, and the review-and-confirm modal.
import { PaperPlaneTilt } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { SelectField, TextField } from "@/components/Field";
import { FormMessage } from "@/components/FormMessage";
import { Modal } from "@/components/Overlay";
import { Notice } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import type { AcademyCardOut, AudiencePreview, Campaign, MailStatus, Page } from "@/lib/types";

import { BlockEditor } from "./BlockEditor";
import { incompleteCount, newDraft, toBlocks, type Draft } from "./blocks";
import { EmailPreview } from "./EmailPreview";
import { AudiencePicker, EMPTY_AUDIENCE, toAudience, type AcademyChoice, type AudienceDraft, type AudienceKind } from "./AudiencePicker";

const MAX_PREHEADER = 140;
const BOARD = "La mesa directiva de UpiixSol";
const MAX_SUBJECT = 150;

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

/** "1 de diciembre": the period end is a UTC midnight, so read it in UTC. */
function renewal(iso: string) {
  const d = new Date(iso);
  return `${d.getUTCDate()} de ${MESES[d.getUTCMonth()]}`;
}

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
      <p className="text-sm text-muted">{`Te quedan ${status.remaining.toLocaleString("en-US")} de ${status.monthly_limit.toLocaleString("en-US")} correos este mes · se renueva el ${renewal(status.period_end)}`}</p>
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
  const [preheader, setPreheader] = useState("");
  const [drafts, setDrafts] = useState<Draft[]>(() => [newDraft("paragraph")]);
  // undefined = follow the audience's club; null = the board; a number = that club (superadmin only).
  const [picked, setPicked] = useState<number | null | undefined>(undefined);
  const [slugs, setSlugs] = useState<Record<number, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [preview, setPreview] = useState<AudiencePreview | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sentNote, setSentNote] = useState<string | null>(null);

  useEffect(() => {
    api<Page<AcademyCardOut>>("/academies", { query: { limit: 50 } })
      .then((page) => setSlugs(Object.fromEntries(page.items.map((a) => [a.id, a.slug]))))
      .catch(() => setSlugs({})); // only the "Ver el club" preset needs it
  }, []);

  const audience = toAudience(draft);
  const off = !status.enabled;
  const blocks = useMemo(() => toBlocks(drafts), [drafts]);
  const unfinished = incompleteCount(drafts);

  // The sender: a club admin's is their club (the server takes it from their account); a superadmin's follows
  // the audience's club until they pick one. The board cannot be picked for a club audience (the server
  // would still send as that club), so that option is off then.
  const audienceClub = draft.kind === "academy" ? draft.academyId : null;
  const senderId = ownClub ? (academies[0]?.id ?? null) : (picked ?? audienceClub);

  const payload = {
    subject: subject.trim() || "Sin asunto",
    audience,
    blocks,
    ...(preheader.trim() ? { preheader: preheader.trim() } : {}),
    ...(!ownClub && senderId !== null ? { sender_academy_id: senderId } : {}),
  };
  const previewPayload = audience && blocks.length > 0 ? payload : null;

  async function review() {
    setSentNote(null);
    if (!subject.trim()) return setFormError("Escribe un asunto.");
    if (blocks.length === 0) return setFormError("Agrega al menos un bloque con contenido.");
    if (unfinished > 0) return setFormError("Completa o elimina los bloques vacíos.");
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
      const created = await api<Campaign>("/mail/campaigns", { method: "POST", json: payload });
      const campaign = await api<Campaign>(`/mail/campaigns/${created.id}/send`, { method: "POST" });
      setPreview(null);
      setSubject("");
      setPreheader("");
      setDrafts([newDraft("paragraph")]);
      setPicked(undefined);
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
  const confirmHint = preview === null ? null : preview.count === 0 ? "Nadie recibiría este correo: cambia los destinatarios." : tooMany ? `Supera tu cupo de este mes (${status.remaining}).` : null;

  return (
    <Card className="grid gap-5 p-5 sm:p-6">
      {off && <Notice tone="alert">El correo está desactivado. Puedes redactar, pero no enviar, hasta que se active.</Notice>}
      <div className="grid items-start gap-6 lg:grid-cols-2">
        <div className="grid min-w-0 content-start gap-5">
          <AudiencePicker draft={draft} onChange={(next) => { setPicked(undefined); setDraft(next); }} academies={academies} kinds={kinds} ownClub={ownClub} />
          {ownClub ? (
            <p className="text-sm">{`Enviado por ${academies[0]?.name ?? ""}`}</p>
          ) : (
            <SelectField label="Enviado por" value={senderId ?? ""} onChange={(e) => setPicked(e.target.value ? Number(e.target.value) : null)}>
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
          <TextField label="Asunto" value={subject} maxLength={MAX_SUBJECT} onChange={(e) => setSubject(e.target.value.replace(/[\r\n]+/g, " "))} />
          <TextField label="Texto de vista previa (opcional)" value={preheader} maxLength={MAX_PREHEADER} hint="Lo que se ve junto al asunto en la bandeja de entrada." onChange={(e) => setPreheader(e.target.value.replace(/[\r\n]+/g, " "))} />
          <BlockEditor drafts={drafts} onChange={setDrafts} clubSlug={senderId === null ? null : (slugs[senderId] ?? null)} />
        </div>
        <div className="min-w-0 lg:sticky lg:top-4">
          <EmailPreview payload={previewPayload} emptyHint={audience ? "Agrega contenido para ver cómo queda el correo." : "Elige a quién enviar el correo para ver la vista previa."} />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" icon={<PaperPlaneTilt weight="bold" />} onClick={() => void review()} disabled={off} loading={checking}>
          Revisar y enviar
        </Button>
      </div>
      <FormMessage message={formError} tone="error" />
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
