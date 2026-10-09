// In-app notifications (owner UPS-021): a transient compact card laid over the top bar + a right-side panel
// behind the bell. The card (layouts/Notifications.tsx) shows only the newest toast, title + action in one
// line: centered in the bar from `sm` up, and on phones from the left edge to just before the bell and the
// user menu, so both stay reachable. The body is read in the bell's panel.
//
//   const { notify } = useNotifications();
//   notify({ id: "welcome", title: "Hola", body: "…", action: { label: "Ver", to: "/x" } });
//
// `id` deduplicates: notifying the same id again updates it instead of stacking a copy.

import { createContext, use, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { useAuth } from "./auth";

export interface AppNotification {
  id: string;
  /** Show the transient card only once per browser session (the bell keeps the notification). */
  oncePerSession?: boolean;
  title: string;
  body?: string;
  tone?: "info" | "warning";
  action?: { label: string; to: string };
}

interface StoredNotification extends AppNotification {
  read: boolean;
  createdAt: number;
}

interface NotificationsValue {
  items: StoredNotification[];
  toasts: AppNotification[];
  unread: number;
  notify: (notification: AppNotification) => void;
  dismiss: (id: string) => void;
  dismissToast: (id: string) => void;
  markAllRead: () => void;
}

const NotificationsContext = createContext<NotificationsValue | null>(null);

// sessionStorage can be unavailable (private mode, blocked storage): then the card simply shows again.
function readSession(key: string): boolean {
  try {
    return window.sessionStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function writeSession(key: string): void {
  try {
    window.sessionStorage.setItem(key, "1");
  } catch {
    /* ignore */
  }
}
const TOAST_MS = 6000;

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<StoredNotification[]>([]);
  const [toasts, setToasts] = useState<AppNotification[]>([]);
  const timers = useRef(new Map<string, number>());

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
    window.clearTimeout(timers.current.get(id));
    timers.current.delete(id);
  }, []);

  const notify = useCallback(
    (notification: AppNotification) => {
      setItems((current) => [
        { ...notification, read: false, createdAt: Date.now() },
        ...current.filter((item) => item.id !== notification.id),
      ]);
      if (notification.oncePerSession) {
        const key = `upx-toast:${notification.id}`;
        if (readSession(key)) return;
        writeSession(key);
      }
      setToasts((current) => [notification, ...current.filter((toast) => toast.id !== notification.id)].slice(0, 3));
      window.clearTimeout(timers.current.get(notification.id));
      timers.current.set(notification.id, window.setTimeout(() => dismissToast(notification.id), TOAST_MS));
    },
    [dismissToast],
  );

  const dismiss = useCallback(
    (id: string) => {
      setItems((current) => current.filter((item) => item.id !== id));
      dismissToast(id);
    },
    [dismissToast],
  );

  const markAllRead = useCallback(() => setItems((current) => current.map((item) => ({ ...item, read: true }))), []);

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((timer) => window.clearTimeout(timer));
  }, []);

  const value = useMemo(
    () => ({
      items,
      toasts,
      unread: items.filter((item) => !item.read).length,
      notify,
      dismiss,
      dismissToast,
      markAllRead,
    }),
    [items, toasts, notify, dismiss, dismissToast, markAllRead],
  );
  return (
    <NotificationsContext value={value}>
      <SessionNotifications />
      {children}
    </NotificationsContext>
  );
}

export function useNotifications(): NotificationsValue {
  const context = use(NotificationsContext);
  if (!context) throw new Error("useNotifications must be used inside <NotificationsProvider>");
  return context;
}

/** Notifications derived from the session (today: the provisional password). */
function SessionNotifications() {
  const { user } = useAuth();
  const { notify, dismiss } = useNotifications();
  const provisional = Boolean(user?.must_change_password);

  useEffect(() => {
    if (provisional) {
      notify({
        id: "provisional-password",
        oncePerSession: true,
        tone: "warning",
        title: "Cambia tu contraseña provisional",
        body: "Entraste con una contraseña temporal. Cámbiala por una que solo tú conozcas.",
        action: { label: "Ir a Seguridad", to: "/cuenta?tab=seguridad" },
      });
    } else {
      dismiss("provisional-password");
    }
  }, [provisional, notify, dismiss]);

  return null;
}
