// The only door to the backend (owner UPS-004). Every route lives under /api.
//
//   const page = await api<Page<PostOut>>("/channels/3/posts", { query: { limit: 20 } });
//   await api<PostOut>("/channels/3/posts", { method: "POST", json: { body } });
//   await api<PostOut>("/channels/3/posts", { method: "POST", form });   // multipart (images)
//
// The access token lives only in memory. On a 401 the client calls /api/auth/refresh once
// (refresh token in an HttpOnly cookie) and retries the request.

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

let accessToken: string | null = null;
let refreshing: Promise<TokenOut | null> | null = null;
const listeners = new Set<(session: TokenOut | null) => void>();

export function setAccessToken(token: string | null): void {
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

/** Single-flight refresh: concurrent 401s share one /auth/refresh call. */
export function refreshSession(): Promise<TokenOut | null> {
  refreshing ??= (async () => {
    try {
      const response = await fetch("/api/auth/refresh", { method: "POST", credentials: "include" });
      const session = response.ok ? ((await response.json()) as TokenOut) : null;
      accessToken = session?.access_token ?? null;
      listeners.forEach((listener) => listener(session));
      return session;
    } catch {
      return null;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { json, form, query, skipRefresh, headers, ...init } = options;
  const send = () => {
    const finalHeaders = new Headers(headers);
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
