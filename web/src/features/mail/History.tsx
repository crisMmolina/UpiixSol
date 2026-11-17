// Send history (spec 003): campaigns with audience, sender, date, status and counts per status.
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ListSkeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import type { Campaign, MailRecipientStatus, Page } from "@/lib/types";

import { KIND_LABEL, ROLE_LABEL, type AcademyChoice } from "./AudiencePicker";

const STALE_MS = 15 * 60 * 1000;
const POLL_MS = 3000;

const COUNT_LABEL: Record<MailRecipientStatus, [string, string]> = {
  pending: ["pendiente", "pendientes"],
  accepted: ["aceptado", "aceptados"],
  delivered: ["entregado", "entregados"],
  failed: ["fallido", "fallidos"],
  bounced: ["rebotado", "rebotados"],
  complained: ["queja", "quejas"],
};

const STATUS: Record<Campaign["status"], { label: string; tone: "neutral" | "primary" | "success" | "alert" | "accent" }> = {
  draft: { label: "Borrador", tone: "neutral" },
  sending: { label: "Enviando", tone: "accent" },
  sent: { label: "Enviado", tone: "success" },
  partial: { label: "Enviado con fallos", tone: "alert" },
  failed: { label: "Falló", tone: "alert" },
};

/** `sending` with no recent start: the process stopped, so the unsent recipients may be resumed. */
export function isStuck(campaign: Campaign, now = Date.now()): boolean {
  if (campaign.status !== "sending") return false;
  const since = Date.parse(campaign.sent_at ?? campaign.created_at);
  return Number.isFinite(since) && now - since > STALE_MS;
}

function audienceText(campaign: Campaign, academies: AcademyChoice[]): string {
  const a = campaign.audience;
  if (a.kind === "academy") return `${KIND_LABEL.academy} · ${academies.find((x) => x.id === a.academy_id)?.name ?? "club"}`;
  if (a.kind === "role") return `${KIND_LABEL.role} · ${ROLE_LABEL[a.role]}`;
  if (a.kind === "individual") {
    const parts = [`${a.user_ids.length} de la plataforma`, `${a.outside} externos`];
    return `${KIND_LABEL.individual} · ${parts.join(", ")}`;
  }
  return KIND_LABEL.all;
}

const DATE = new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" });

function when(value: string): string {
  const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`);
  return Number.isFinite(t) ? DATE.format(t) : "";
}

export function History({ academies, reloadKey = 0 }: { academies: AcademyChoice[]; reloadKey?: number }) {
  const [items, setItems] = useState<Campaign[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [more, setMore] = useState(false);

  const load = useCallback(async () => {
    try {
      const page = await api<Page<Campaign>>("/mail/campaigns", { query: { limit: 20 } });
      setItems(page.items);
      setCursor(page.next_cursor);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  const sending = items?.some((c) => c.status === "sending" && !isStuck(c)) ?? false;
  useEffect(() => {
    if (!sending) return;
    const timer = window.setInterval(() => void load(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [sending, load]);

  async function loadMore() {
    if (!cursor) return;
    setMore(true);
    try {
      const page = await api<Page<Campaign>>("/mail/campaigns", { query: { limit: 20, cursor } });
      setItems((prev) => [...(prev ?? []), ...page.items]);
      setCursor(page.next_cursor);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setMore(false);
    }
  }

  async function resume(campaign: Campaign) {
    setBusy(campaign.id);
    try {
      const updated = await api<Campaign>(`/mail/campaigns/${campaign.id}/resume`, { method: "POST" });
      setItems((prev) => prev?.map((c) => (c.id === updated.id ? updated : c)) ?? prev);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section aria-label="Historial" className="grid gap-3">
      <h2 className="text-2xl">Historial</h2>
      {error && items && <p role="alert" className="text-sm font-semibold text-accent-2">{error}</p>}
      {!items ? (
        error ? <ErrorState message={error} onRetry={() => void load()} /> : <ListSkeleton rows={3} />
      ) : items.length === 0 ? (
        <EmptyState title="Aún no hay envíos" description="Cuando envíes un correo aparecerá aquí con su estado." />
      ) : (
        <Card>
          <ul className="divide-y divide-line">
            {items.map((c) => {
              const stuck = isStuck(c);
              const state = stuck ? { label: "Interrumpido", tone: "alert" as const } : STATUS[c.status];
              const counts = (Object.keys(COUNT_LABEL) as MailRecipientStatus[]).filter((k) => (c.counts_by_status[k] ?? 0) > 0);
              return (
                <li key={c.id} className="grid gap-1.5 px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="min-w-0 flex-1 basis-48 break-words font-semibold">{c.subject}</p>
                    <Badge tone={state.tone}>{state.label}</Badge>
                    {stuck && (
                      <Button size="sm" variant="secondary" loading={busy === c.id} onClick={() => void resume(c)}>
                        Reanudar
                      </Button>
                    )}
                  </div>
                  <p className="text-sm text-muted">{audienceText(c, academies)}</p>
                  <p className="text-sm text-muted">
                    <span>{c.sender?.nickname ?? "—"}</span> · <span>{when(c.created_at)}</span> · <span>{`${c.recipient_count} ${c.recipient_count === 1 ? "destinatario" : "destinatarios"}`}</span>
                  </p>
                  {counts.length > 0 && (
                    <p className="flex flex-wrap gap-x-3 text-sm tabular-nums">
                      {counts.map((k) => {
                        const n = c.counts_by_status[k] ?? 0;
                        return <span key={k}>{`${n} ${COUNT_LABEL[k][n === 1 ? 0 : 1]}`}</span>;
                      })}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
          {cursor && (
            <div className="border-t border-line p-3 text-center">
              <Button variant="secondary" loading={more} onClick={() => void loadMore()}>
                Cargar más
              </Button>
            </div>
          )}
        </Card>
      )}
    </section>
  );
}
