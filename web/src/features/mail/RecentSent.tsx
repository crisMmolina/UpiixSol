// "Enviados recientes": the sender's last 6 sent emails in scope; "Usar de nuevo" loads subject, preview text and
// blocks, never the recipients (UPS-106 contract: GET /api/mail/campaigns and /campaigns/{id}).
import { ArrowsClockwise } from "@phosphor-icons/react";

import type { Campaign } from "@/lib/types";

const dateFormat = new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short", year: "numeric", timeZone: "America/Mexico_City" });

/** Sent (or being sent) first-hand emails, newest first, at most 6. */
export function recentSent(campaigns: Campaign[]): Campaign[] {
  return campaigns.filter((c) => c.status === "sent" || c.status === "partial" || c.status === "sending").slice(0, 6);
}

export function RecentSent({ items, busyId, onReuse }: { items: Campaign[]; busyId: number | null; onReuse: (campaign: Campaign) => void }) {
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="recent-sent" className="grid gap-3">
      <h3 id="recent-sent" className="font-display text-lg font-semibold">
        Enviados recientes
      </h3>
      <ul className="grid gap-2 sm:grid-cols-2">
        {items.map((c) => (
          <li key={c.id} className="flex items-center justify-between gap-3 rounded-2xl border border-line bg-surface p-3 pl-4">
            <span className="grid min-w-0">
              <span className="truncate font-semibold">{c.subject}</span>
              <span className="text-sm text-muted">{c.sent_at ? dateFormat.format(new Date(c.sent_at)) : "Enviándose"}</span>
            </span>
            <button
              type="button"
              aria-label={`Usar de nuevo: ${c.subject}`}
              disabled={busyId !== null}
              onClick={() => onReuse(c)}
              className="inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-full px-3 text-sm font-semibold text-link hover:bg-subtle focus-visible:outline-3 disabled:opacity-60"
            >
              <ArrowsClockwise weight="bold" aria-hidden />
              Usar de nuevo
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
