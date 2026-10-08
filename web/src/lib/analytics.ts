// Usage analytics tracker (UPS-037). Events land in `activity_events` through POST /api/analytics/events.
//
//   import { track } from "@/lib/analytics";
//   track("video.play", { subject_type: "lesson", subject_id: lesson.id, academy_slug: slug, properties: { position_s: 42 } });
//
// - Batches: flushes every ~10 s or at 20 queued events, and once more when the tab is hidden.
// - Auth: the API only takes events from signed-in users. `navigator.sendBeacon` cannot send the
//   Authorization header and the refresh cookie only travels to /api/auth, so the page-hide flush is a
//   `fetch` with `keepalive: true` through api() (in-memory access token, one refresh on 401). keepalive
//   survives the page closing, like a beacon. See docs/analytics.md.
// - Does nothing while signed out (`setAnalyticsUser(null)`), never throws, never blocks the UI, and turns
//   itself off for the rest of the page's life after a 4xx it cannot recover from (invalid batch, 429...).
// - Properties: ids, slugs, route templates and counters only. Never names, emails, boletas or search text.

import { ApiError, api } from "./api";

export type WebEventName =
  | "page.view"
  | "video.play"
  | "video.pause"
  | "video.ended"
  | "video.progress"
  | "search.performed"
  | "resource.opened"
  | "link.opened";

export type SubjectType = "academy" | "route" | "lesson" | "resource" | "post" | "channel" | "project" | "blog" | "event";

export interface TrackData {
  /** Route template, e.g. "/a/:slug/clases/:lessonId" (never the raw URL with ids). */
  path?: string;
  subject_type?: SubjectType;
  subject_id?: number;
  /** Club the event belongs to, so the dashboard can slice per club. */
  academy_slug?: string;
  /** Small (≤ 2 KB), flat, no PII. */
  properties?: Record<string, string | number | boolean | null>;
}

interface QueuedEvent extends TrackData {
  name: WebEventName;
  occurred_at: string;
}

const FLUSH_MS = 10_000;
const FLUSH_AT = 20;
const MAX_BATCH = 50; // server limit
const SESSION_KEY = "upx-analytics-session";

let userId: number | null = null;
let disabled = false;
let queue: QueuedEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let listening = false;
let memorySession: string | null = null;

function newId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  }
}

/** One id per browser tab (sessionStorage), so a dashboard can group a visit. */
function sessionId(): string {
  try {
    const stored = sessionStorage.getItem(SESSION_KEY);
    if (stored) return stored;
    const created = newId();
    sessionStorage.setItem(SESSION_KEY, created);
    return created;
  } catch {
    memorySession ??= newId();
    return memorySession;
  }
}

function onHide(): void {
  if (document.visibilityState === "hidden") void flush(true);
}

function listen(): void {
  if (listening || typeof document === "undefined") return;
  listening = true;
  document.addEventListener("visibilitychange", onHide);
  window.addEventListener("pagehide", () => void flush(true));
}

/** Who is signed in (null = nobody: queued events are dropped and nothing is sent). */
export function setAnalyticsUser(id: number | null): void {
  try {
    if (id !== userId) queue = []; // never send one account's events under another session
    userId = id;
    if (id !== null) listen();
  } catch {
    // analytics never breaks the app
  }
}

/** Queue one usage event. Safe to call anywhere: it never throws and never awaits the network. */
export function track(name: WebEventName, data: TrackData = {}): void {
  try {
    if (userId === null || disabled) return;
    queue.push({ name, occurred_at: new Date().toISOString(), ...data });
    if (queue.length > MAX_BATCH) queue.splice(0, queue.length - MAX_BATCH);
    if (queue.length >= FLUSH_AT) void flush();
    else timer ??= setTimeout(() => void flush(), FLUSH_MS);
  } catch {
    // analytics never breaks the app
  }
}

/** Send what is queued. `keepalive` lets the request outlive the page (page hide). */
export async function flush(keepalive = false): Promise<void> {
  try {
    if (timer !== null) clearTimeout(timer);
    timer = null;
    if (userId === null || disabled || queue.length === 0) return;
    const events = queue.splice(0, MAX_BATCH);
    await api<{ accepted: number }>("/analytics/events", {
      method: "POST",
      json: { session_id: sessionId(), events },
      keepalive,
    });
  } catch (error) {
    // The batch is dropped either way: analytics never retries or blocks the UI.
    // 401 (session ended) and a pending password change are not the tracker's fault; any other 4xx is.
    if (
      error instanceof ApiError &&
      error.status >= 400 &&
      error.status < 500 &&
      error.status !== 401 &&
      error.code !== "password_change_required"
    ) {
      disabled = true;
      queue = [];
    }
  }
}
