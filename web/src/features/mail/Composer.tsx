// Composer (specs 003, 004, 005): three steps (Plantilla → Contenido → Destinatarios y envío) over one reducer,
// the step in the URL (merged into the existing search params), a local draft, and the review-and-confirm modal.
import { useEffect, useMemo, useReducer, useState } from "react";
import { useSearchParams } from "react-router";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { FormMessage } from "@/components/FormMessage";
import { Modal } from "@/components/Overlay";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AcademyCardOut, AudiencePreview, Campaign, MailStatus, Page } from "@/lib/types";

import { toAudience, type AcademyChoice, type AudienceKind } from "./AudiencePicker";
import { incompleteCount, toBlocks } from "./blocks";
import { Stepper } from "./ComposerSteps";
import {
  clearDraft,
  composerReducer,
  plural,
  renewal,
  initialState,
  isDirty,
  loadDraft,
  parseStep,
  saveDraft,
  type Step,
  type StoredDraft,
} from "./composerState";
import { ContentStep } from "./ContentStep";
import { replyToError } from "./ReplyToField";
import { SendStep } from "./SendStep";
import { TemplateStep } from "./TemplateStep";

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
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [search, setSearch] = useSearchParams();
  const step = parseStep(search.get("paso"));
  const [state, dispatch] = useReducer(composerReducer, undefined, () => initialState(kinds, ownClub, academies));
  const [slugs, setSlugs] = useState<Record<number, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [preview, setPreview] = useState<AudiencePreview | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [sentNote, setSentNote] = useState<string | null>(null);
  // Local draft: `ready` once the stored one was checked; `pending` while the sender has not answered the prompt.
  const [ready, setReady] = useState(false);
  const [pending, setPending] = useState<StoredDraft | null>(null);

  /** Only `paso` changes: `tab` (the superadmin panel) and anything else in the URL stay. */
  function goTo(next: Step) {
    setSearch(
      (current) => {
        const merged = new URLSearchParams(current);
        merged.set("paso", next);
        return merged;
      },
      { replace: false },
    );
    setFormError(null);
  }

  useEffect(() => {
    api<Page<AcademyCardOut>>("/academies", { query: { limit: 50 } })
      .then((page) => setSlugs(Object.fromEntries(page.items.map((a) => [a.id, a.slug]))))
      .catch(() => setSlugs({})); // only the "Ver el club" preset needs it
  }, []);

  // Reply-To starts as the server's default (MAIL_REPLY_TO); anything typed before it arrives wins.
  useEffect(() => {
    api<{ reply_to: string | null }>("/mail/reply-to")
      .then((out) => dispatch({ type: "defaultReplyTo", value: out.reply_to ?? "" }))
      .catch(() => undefined); // no default is fine: the server falls back to its own
  }, []);

  // On mount: someone else's draft is deleted (logout, shared computer); ours is offered, never applied silently.
  useEffect(() => {
    if (userId === null) return;
    setPending(loadDraft(userId));
    setReady(true);
  }, [userId]);

  // Keep the draft while the sender edits (and not while the prompt is open: the stored one must survive it).
  const dirty = isDirty(state);
  useEffect(() => {
    if (!ready || pending || userId === null) return;
    const timer = window.setTimeout(() => (dirty ? saveDraft(userId, state) : clearDraft()), 300);
    return () => window.clearTimeout(timer);
  }, [ready, pending, userId, state, dirty]);

  const audience = toAudience(state.audience);
  const blocks = useMemo(() => toBlocks(state.drafts), [state.drafts]);
  const unfinished = incompleteCount(state.drafts);

  // The sender: a club admin's is their club (the server takes it from their account); a superadmin's follows
  // the audience's club until they pick one. The board cannot be picked for a club audience (the server
  // would still send as that club), so that option is off then.
  const audienceClub = state.audience.kind === "academy" ? state.audience.academyId : null;
  const senderId = ownClub ? (academies[0]?.id ?? null) : state.sender === "auto" ? audienceClub : state.sender;
  const { subject, preheader, replyTo } = state;

  const payload = {
    subject: subject.trim() || "Sin asunto",
    audience,
    blocks,
    ...(preheader.trim() ? { preheader: preheader.trim() } : {}),
    ...(replyTo.trim() && !replyToError(replyTo) ? { reply_to: replyTo.trim() } : {}),
    ...(!ownClub && senderId !== null ? { sender_academy_id: senderId } : {}),
  };
  // Rendering needs no recipients: until they are chosen the preview is drawn for the whole club.
  const previewPayload = blocks.length > 0 ? { ...payload, audience: audience ?? { kind: "all" } } : null;

  async function review() {
    setSentNote(null);
    if (!subject.trim()) return fail("Escribe un asunto.", "contenido");
    if (blocks.length === 0) return fail("Agrega al menos un bloque con contenido.", "contenido");
    if (unfinished > 0) return fail("Completa o elimina los bloques vacíos.", "contenido");
    if (!audience) return fail("Elige a quién enviar el correo.");
    if (replyToError(replyTo)) return fail("Corrige el correo de respuesta.");
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

  /** A content problem sends the sender back to the content step, where the message is shown. */
  function fail(message: string, to?: Step) {
    if (to && to !== step) goTo(to); // goTo clears the message, so set it after
    setFormError(message);
  }

  async function confirm() {
    if (!audience || sending) return;
    setSending(true);
    setSendError(null);
    try {
      const created = await api<Campaign>("/mail/campaigns", { method: "POST", json: payload });
      const campaign = await api<Campaign>(`/mail/campaigns/${created.id}/send`, { method: "POST" });
      setPreview(null);
      clearDraft();
      dispatch({ type: "reset", state: { ...initialState(kinds, ownClub, academies), replyTo: state.replyTo, audience: { ...initialState(kinds, ownClub, academies).audience, kind: state.audience.kind, academyId: state.audience.academyId } } });
      goTo("plantilla");
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
  const common = {
    state,
    dispatch,
    clubSlug: senderId === null ? null : (slugs[senderId] ?? null),
    eventsAcademy: ownClub ? (slugs[academies[0]?.id ?? 0] ?? undefined) : null,
    previewPayload,
  };

  return (
    <Card className="grid gap-7 p-5 sm:p-8">
      <Stepper step={step} onGo={goTo} />
      {pending && (
        <div role="status" className="flex flex-col gap-3 rounded-2xl border border-line bg-subtle p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm">
            <span className="font-semibold">Tienes un borrador sin enviar.</span>{" "}
            <span className="text-muted">{`Guardado en este navegador${pending.state.subject.trim() ? `: «${pending.state.subject.trim()}»` : ""}.`}</span>
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => { dispatch({ type: "restore", state: pending.state }); setPending(null); }}>
              Restaurar borrador
            </Button>
            <Button size="sm" variant="ghost" onClick={() => { clearDraft(); setPending(null); }}>
              Descartar
            </Button>
          </div>
        </div>
      )}
      {step === "plantilla" && <TemplateStep onNext={() => goTo("contenido")} />}
      {step === "contenido" && (
        <>
          <ContentStep {...common} onBack={() => goTo("plantilla")} onNext={() => goTo("envio")} />
          <FormMessage message={formError} tone="error" />
        </>
      )}
      {step === "envio" && (
        <SendStep
          {...common}
          onBack={() => goTo("contenido")}
          status={status}
          academies={academies}
          kinds={kinds}
          ownClub={ownClub}
          senderId={senderId}
          audienceClub={audienceClub}
          formError={formError}
          checking={checking}
          onReview={() => void review()}
        />
      )}
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
