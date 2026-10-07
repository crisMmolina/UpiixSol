// The only door to the backend (owner UPS-004). Every route lives under /api.
//
//   const page = await api<Page<PostOut>>("/channels/3/posts", { query: { limit: 20 } });
//   await api<PostOut>("/channels/3/posts", { method: "POST", json: { body } });
//   await api<PostOut>("/channels/3/posts", { method: "POST", form });   // multipart (images)
//
// The access token lives only in memory. On a 401 the client calls /api/auth/refresh once
// (refresh token in an HttpOnly cookie) and retries the request. Every request carries
// `X-Requested-With: fetch`: the API requires it on cookie-authenticated endpoints (CSRF guard).

import type { ApiError as ApiErrorBody, TokenOut } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface ApiOptions extends Omit<RequestInit, "body"> {
  json?: unknown;
  form?: FormData;
  query?: Query;
  /** Internal: do not try to refresh on 401 (used by the auth endpoints themselves). */
  skipRefresh?: boolean;
}

const CSRF_HEADER = { "X-Requested-With": "fetch" };

let accessToken: string | null = null;
let refreshing: Promise<TokenOut | null> | null = null;
// Bumped by every explicit login/logout: a refresh that started before it is stale and ignored,
// so a slow startup refresh can never undo a login (or bring back a session after logout).
let sessionEpoch = 0;
const listeners = new Set<(session: TokenOut | null) => void>();

/** Explicit session change (login, register, logout). */
export function setAccessToken(token: string | null): void {
  sessionEpoch += 1;
  accessToken = token;
}

/** Subscribe to session changes caused by refreshes or expiry (used by AuthProvider). */
export function onSessionChange(listener: (session: TokenOut | null) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function buildUrl(path: string, query?: Query): string {
  const url = `/api${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function toError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body?.error) return new ApiError(response.status, body.error.code, body.error.message, body.error.details);
  } catch {
    // non-JSON error (proxy, network): fall through
  }
  return new ApiError(response.status, "http_error", "No pudimos completar la solicitud. Intenta de nuevo.");
}

/** Single-flight refresh: concurrent 401s share one /auth/refresh call. Listeners get the result. */
export function refreshSession(): Promise<TokenOut | null> {
  refreshing ??= (async () => {
    const epoch = sessionEpoch;
    let session: TokenOut | null = null;
    try {
      const response = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
        headers: CSRF_HEADER,
      });
      session = response.ok ? ((await response.json()) as TokenOut) : null;
    } catch {
      session = null; // network error: treat as no session
    } finally {
      refreshing = null;
    }
    if (epoch !== sessionEpoch) return null; // a login/logout happened meanwhile: drop this result
    accessToken = session?.access_token ?? null;
    listeners.forEach((listener) => listener(session));
    return session;
  })();
  return refreshing;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { json, form, query, skipRefresh, headers, ...init } = options;
  const send = () => {
    const finalHeaders = new Headers(headers);
    finalHeaders.set("X-Requested-With", CSRF_HEADER["X-Requested-With"]);
    if (json !== undefined) finalHeaders.set("Content-Type", "application/json");
    if (accessToken) finalHeaders.set("Authorization", `Bearer ${accessToken}`);
    return fetch(buildUrl(path, query), {
      credentials: "include",
      ...init,
      headers: finalHeaders,
      body: form ?? (json !== undefined ? JSON.stringify(json) : undefined),
    });
  };

  let response = await send();
  if (response.status === 401 && !skipRefresh) {
    const session = await refreshSession();
    if (session) response = await send();
  }
  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Human message for any thrown value (es-MX). */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Algo salió mal. Revisa tu conexión e intenta de nuevo.";
}
