// Delivery detail of one sent email (spec 006): who got it, per status, with the reason for bounces and failures.
import { ArrowLeft, MagnifyingGlass } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ListSkeleton } from "@/components/Skeleton";
import { ErrorState } from "@/components/States";
import { api, errorMessage } from "@/lib/api";
import type { CampaignDetail, DeliveryRow, MailRecipientStatus, Page } from "@/lib/types";

const PAGE_SIZE = 20;
const SEARCH_DELAY_MS = 300;

const DATE = new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" });

export function when(value: string): string {
  const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`);
  return Number.isFinite(t) ? DATE.format(t) : "";
}

const TABS: { status: MailRecipientStatus; label: string; empty: string }[] = [
  { status: "delivered", label: "Entregados", empty: "Todavía no hay entregas confirmadas." },
  { status: "bounced", label: "Rebotados", empty: "Ningún correo rebotó." },
  { status: "failed", label: "Fallidos", empty: "Ningún envío falló." },
  { status: "complained", label: "Marcados como spam", empty: "Nadie lo marcó como spam." },
  { status: "accepted", label: "En camino", empty: "Nada en camino: todo tiene ya un resultado." },
  { status: "pending", label: "Sin enviar", empty: "Nadie quedó sin enviar." },
];

export function DeliveryDetail({ campaignId, subject, onBack }: { campaignId: number; subject: string; onBack: () => void }) {
  const [, setSearch] = useSearchParams();
  const [detail, setDetail] = useState<CampaignDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<MailRecipientStatus>("delivered");
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<DeliveryRow[] | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [more, setMore] = useState(false);
  const tabRefs = useRef<Partial<Record<MailRecipientStatus, HTMLButtonElement | null>>>({});
  const heading = useRef<HTMLHeadingElement>(null);
  const request = useRef(0); // answers of an older tab or search are dropped

  // The history sits below the composer: bring the detail into view and announce it to keyboard and screen readers.
  useEffect(() => {
    heading.current?.scrollIntoView({ block: "start" });
    heading.current?.focus({ preventScroll: true });
  }, []);

  useEffect(() => {
    api<CampaignDetail>(`/mail/campaigns/${campaignId}`)
      .then((out) => {
        setDetail(out);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [campaignId]);

  useEffect(() => {
    const timer = window.setTimeout(() => setQ(text.trim()), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [text]);

  const purged = detail?.details_purged ?? false;
  const loadFirst = useCallback(async () => {
    const mine = ++request.current;
    setRows(null);
    setListError(null);
    try {
      const page = await api<Page<DeliveryRow>>(`/mail/campaigns/${campaignId}/recipients`, {
        query: { status, q: q || undefined, limit: PAGE_SIZE },
      });
      if (mine !== request.current) return;
      setRows(page.items);
      setCursor(page.next_cursor);
    } catch (err) {
      if (mine === request.current) setListError(errorMessage(err));
    }
  }, [campaignId, status, q]);

  useEffect(() => {
    if (detail && !purged) void loadFirst();
  }, [detail, purged, loadFirst]);

  async function loadMore() {
    if (!cursor) return;
    const mine = request.current;
    setMore(true);
    try {
      const page = await api<Page<DeliveryRow>>(`/mail/campaigns/${campaignId}/recipients`, {
        query: { status, q: q || undefined, limit: PAGE_SIZE, cursor },
      });
      if (mine !== request.current) return;
      setRows((prev) => [...(prev ?? []), ...page.items]);
      setCursor(page.next_cursor);
    } catch (err) {
      setListError(errorMessage(err));
    } finally {
      setMore(false);
    }
  }

  function reuse() {
    // Only `paso` and `reusar` change: `tab` (the panel) and anything else in the URL stay.
    setSearch((current) => {
      const merged = new URLSearchParams(current);
      merged.set("paso", "plantilla");
      merged.set("reusar", String(campaignId));
      return merged;
    });
  }

  function onKey(event: KeyboardEvent, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? TABS.length - 1 : (index + step + TABS.length) % TABS.length;
    setStatus(TABS[next].status);
    tabRefs.current[TABS[next].status]?.focus();
  }

  const current = TABS.find((t) => t.status === status) ?? TABS[0];

  return (
    <section aria-label="Entregas" className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="ghost" size="sm" icon={<ArrowLeft weight="bold" />} onClick={onBack}>
          Volver al historial
        </Button>
        <Button size="sm" variant="secondary" className="ml-auto" onClick={reuse} disabled={!detail}>
          Usar de nuevo
        </Button>
      </div>
      <h2 ref={heading} tabIndex={-1} className="scroll-mt-20 break-words text-2xl outline-none">{subject}</h2>

      {error ? (
        <ErrorState message={error} />
      ) : !detail ? (
        <ListSkeleton rows={3} />
      ) : (
        <Card>
          <div role="tablist" aria-label="Estado de la entrega" className="flex flex-wrap gap-1 border-b border-line p-2">
            {TABS.map(({ status: s, label }, i) => {
              const n = detail.counts_by_status[s] ?? 0;
              return (
                <button
                  key={s}
                  ref={(el) => {
                    tabRefs.current[s] = el;
                  }}
                  type="button"
                  role="tab"
                  id={`entregas-tab-${s}`}
                  aria-selected={status === s}
                  aria-controls="entregas-panel"
                  tabIndex={status === s ? 0 : -1}
                  onClick={() => setStatus(s)}
                  onKeyDown={(e) => onKey(e, i)}
                  className={`min-h-11 rounded-full px-3 text-sm font-semibold ${status === s ? "bg-ink text-surface" : "text-muted hover:bg-line/50 hover:text-ink"}`}
                >
                  {label} <span className="tabular-nums">{n}</span>
                </button>
              );
            })}
          </div>
          <div role="tabpanel" id="entregas-panel" aria-labelledby={`entregas-tab-${status}`} className="grid gap-3 p-4">
            {purged ? (
              <p className="text-sm text-muted">El detalle por persona se borra al año del envío. Los totales de arriba se conservan.</p>
            ) : (
              <>
                <label className="relative block">
                  <span className="sr-only">Buscar por nombre o correo</span>
                  <MagnifyingGlass aria-hidden className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                  <input
                    type="search"
                    role="searchbox"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Buscar por nombre o correo"
                    className="min-h-11 w-full rounded-full border border-line bg-surface pl-9 pr-4 text-sm"
                  />
                </label>
                {listError && (
                  <p role="alert" className="text-sm font-semibold text-accent-2">
                    {listError}
                  </p>
                )}
                {!rows ? (
                  listError ? null : <ListSkeleton rows={3} />
                ) : rows.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted">{q ? "Nadie coincide con la búsqueda." : current.empty}</p>
                ) : (
                  <ul aria-label="Personas" className="divide-y divide-line">
                    {rows.map((r, i) => (
                      <li key={`${r.email}-${i}`} className="grid gap-0.5 py-2.5">
                        <div className="flex flex-wrap items-baseline gap-x-3">
                          <p className="min-w-0 break-words font-semibold">{r.name}</p>
                          <time dateTime={r.updated_at} className="text-xs text-muted">
                            {when(r.updated_at)}
                          </time>
                        </div>
                        {r.email !== r.name && <p className="break-all text-sm text-muted">{r.email}</p>}
                        {r.reason && (
                          <p className="text-sm">
                            {r.reason}
                            {r.reason_code && <span className="text-xs text-muted"> ({r.reason_code})</span>}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                {cursor && (
                  <div className="text-center">
                    <Button variant="secondary" loading={more} onClick={() => void loadMore()}>
                      Cargar más
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </Card>
      )}
    </section>
  );
}
