import { Bell, BellSimpleSlash, Warning, X } from "@phosphor-icons/react";
import { useState, type CSSProperties } from "react";
import { Link } from "react-router";

import { Drawer } from "@/components/Overlay";
import { useNotifications, type AppNotification } from "@/lib/notifications";

/** Bell in the top bar: unread count + a right-side panel with every notification of the session. */
export function NotificationBell() {
  const { items, unread, dismiss, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        aria-label={unread ? `Notificaciones (${unread} sin leer)` : "Notificaciones"}
        onClick={() => {
          setOpen(true);
          markAllRead();
        }}
        className="relative grid size-11 place-items-center rounded-full text-ink transition hover:bg-line/60"
      >
        <Bell size={22} weight={unread ? "fill" : "regular"} aria-hidden />
        {unread > 0 && (
          <span className="absolute right-1.5 top-1.5 grid min-w-4.5 place-items-center rounded-full bg-accent-2 px-1 text-[0.65rem] font-bold leading-4.5 text-white">
            {unread}
          </span>
        )}
      </button>
      <Drawer open={open} onClose={() => setOpen(false)} title="Notificaciones" side="right">
        {items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-10 text-center text-muted">
            <BellSimpleSlash size={32} aria-hidden />
            <p>No tienes notificaciones.</p>
          </div>
        ) : (
          <ul className="grid gap-3">
            {items.map((item, index) => (
              <li key={item.id} className="enter" style={{ "--i": index } as CSSProperties}>
                <NotificationCard notification={item} onDismiss={() => dismiss(item.id)} onAction={() => setOpen(false)} />
              </li>
            ))}
          </ul>
        )}
      </Drawer>
    </>
  );
}

/**
 * Transient cards; they leave on their own after a few seconds (the bell keeps them). Page headers keep their
 * actions top-right ("Ver como miembro") and lists and forms keep theirs at the bottom ("Publicar"), so the
 * newest toast shows as one compact card (title + action) laid over the app's top bar, never over the page
 * (on phones it stops short of the bell and the user menu, so those stay reachable).
 * The full text stays in the bell's panel.
 */
export function Toasts() {
  const { toasts, dismissToast } = useNotifications();
  if (toasts.length === 0) return null;
  return (
    <section
      aria-label="Avisos"
      aria-live="polite"
      className="fixed left-2 right-[8.5rem] top-1 z-40 grid grid-cols-1 [&>*+*]:hidden sm:right-auto sm:left-1/2 sm:w-[26rem] sm:-translate-x-1/2"
    >
      {toasts.map((toast) => (
        <div key={toast.id} className="animate-toast-in rounded-card border border-line bg-surface shadow-lift">
          <NotificationCard notification={toast} compact onDismiss={() => dismissToast(toast.id)} onAction={() => dismissToast(toast.id)} />
        </div>
      ))}
    </section>
  );
}

function NotificationCard({
  notification,
  onDismiss,
  onAction,
  compact = false,
}: {
  notification: AppNotification;
  /** One line of title + the action, so the toast fits over the 64 px top bar. */
  compact?: boolean;
  onDismiss: () => void;
  onAction: () => void;
}) {
  // Compact and full layouts pick their classes outright (two conflicting utilities would race in the CSS order).
  const pick = (full: string, small: string) => (compact ? small : full);
  return (
    <div className={`flex rounded-card bg-surface ring-1 ring-line ${pick("gap-3 p-4", "items-center gap-2 p-2 pl-3")}`}>
      {notification.tone === "warning" && (
        <span className={`grid shrink-0 place-items-center rounded-full bg-accent/20 text-ink ${pick("size-9", "size-8 max-sm:hidden")}`}>
          <Warning size={18} weight="bold" aria-hidden />
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className={`font-semibold leading-snug ${pick("", "truncate text-sm")}`}>{notification.title}</p>
        {notification.body && !compact && <p className="mt-0.5 text-sm text-muted">{notification.body}</p>}
        {notification.action && (
          <Link to={notification.action.to} onClick={onAction} className={`text-sm font-semibold ${pick("mt-2 inline-block", "block")}`}>
            {notification.action.label}
          </Link>
        )}
      </div>
      <button
        type="button"
        aria-label="Descartar"
        onClick={onDismiss}
        className={`grid shrink-0 place-items-center rounded-full text-muted hover:bg-subtle hover:text-ink ${pick("size-8", "size-10")}`}
      >
        <X size={16} weight="bold" />
      </button>
    </div>
  );
}
