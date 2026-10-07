// Session state for the whole app (owner UPS-004). Endpoints are implemented by UPS-005:
//   POST /api/auth/login · /register · /refresh · /logout  → TokenOut (+ refresh cookie)
//   GET  /api/auth/me                                       → UserMe

import { createContext, use, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { PageSkeleton } from "@/components/Skeleton";

import { api, onSessionChange, refreshSession, setAccessToken } from "./api";
import type { LoginIn, RegisterIn, Role, TokenOut, UserMe } from "./types";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: Status;
  user: UserMe | null;
  login: (data: LoginIn) => Promise<UserMe>;
  register: (data: RegisterIn) => Promise<UserMe>;
  logout: () => Promise<void>;
  /** Re-read the current user (after profile/email changes). */
  reload: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Where each role lands after login (IDEA §2.2). */
export function homeFor(user: Pick<UserMe, "role">): string {
  if (user.role === "superadmin") return "/admin";
  if (user.role === "academy_admin") return "/panel/academia";
  return "/";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<UserMe | null>(null);

  // UI state only. Refresh results arrive through onSessionChange (already epoch-checked in api.ts).
  const showSession = useCallback((session: TokenOut | null) => {
    setUser(session?.user ?? null);
    setStatus(session ? "authenticated" : "anonymous");
  }, []);

  // Explicit login/register/logout: owns the token and invalidates any refresh in flight.
  const applySession = useCallback(
    (session: TokenOut | null) => {
      setAccessToken(session?.access_token ?? null);
      showSession(session);
    },
    [showSession],
  );

  useEffect(() => {
    const unsubscribe = onSessionChange(showSession);
    // Restore the session from the refresh cookie on first load.
    void refreshSession();
    return unsubscribe;
  }, [showSession]);

  const login = useCallback(
    async (data: LoginIn) => {
      const session = await api<TokenOut>("/auth/login", { method: "POST", json: data, skipRefresh: true });
      applySession(session);
      return session.user;
    },
    [applySession],
  );

  const register = useCallback(
    async (data: RegisterIn) => {
      const session = await api<TokenOut>("/auth/register", { method: "POST", json: data, skipRefresh: true });
      applySession(session);
      return session.user;
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    try {
      await api<void>("/auth/logout", { method: "POST", skipRefresh: true });
    } finally {
      applySession(null);
    }
  }, [applySession]);

  const reload = useCallback(async () => {
    setUser(await api<UserMe>("/auth/me"));
  }, []);

  const value = useMemo(
    () => ({ status, user, login, register, logout, reload }),
    [status, user, login, register, logout, reload],
  );
  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthContextValue {
  const context = use(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

/** Route guard: anonymous → /login?next=…; wrong role → that role's home. UI only; the API enforces too. */
export function RequireRole({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "loading") return <PageSkeleton />;
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user)} replace />;
  return <>{children}</>;
}
