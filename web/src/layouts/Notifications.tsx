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

/** Transient cards top-right; they leave on their own after a few seconds (the bell keeps them). */
export function Toasts() {
  const { toasts, dismissToast } = useNotifications();
  if (toasts.length === 0) return null;
  return (
    <section aria-label="Avisos" aria-live="polite" className="fixed right-4 top-20 z-40 grid w-[min(22rem,calc(100vw-2rem))] gap-2">
      {toasts.map((toast) => (
        <div key={toast.id} className="animate-toast-in rounded-card border border-line bg-surface shadow-lift">
          <NotificationCard notification={toast} onDismiss={() => dismissToast(toast.id)} onAction={() => dismissToast(toast.id)} />
        </div>
      ))}
    </section>
  );
}

function NotificationCard({
  notification,
  onDismiss,
  onAction,
}: {
  notification: AppNotification;
  onDismiss: () => void;
  onAction: () => void;
}) {
  return (
    <div className="flex gap-3 rounded-card bg-surface p-4 ring-1 ring-line">
      {notification.tone === "warning" && (
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-accent/20 text-ink">
          <Warning size={18} weight="bold" aria-hidden />
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="font-semibold leading-snug">{notification.title}</p>
        {notification.body && <p className="mt-0.5 text-sm text-muted">{notification.body}</p>}
        {notification.action && (
          <Link to={notification.action.to} onClick={onAction} className="mt-2 inline-block text-sm font-semibold">
            {notification.action.label}
          </Link>
        )}
      </div>
      <button type="button" aria-label="Descartar" onClick={onDismiss} className="grid size-8 shrink-0 place-items-center rounded-full text-muted hover:bg-subtle hover:text-ink">
        <X size={16} weight="bold" />
      </button>
    </div>
  );
}
