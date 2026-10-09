// Flow step 1 (UPS-005): single login for every role + member self-registration.
import { useState } from "react";
import { Navigate, useNavigate, useSearchParams, type RouteObject } from "react-router";

import { AnimatedHeight } from "@/components/Motion";
import { PageSkeleton } from "@/components/Skeleton";
import { homeFor, useAuth } from "@/lib/auth";
import { LOGO_HEIGHT, useSite, Wordmark } from "@/lib/brand";
import { AcademyTheme, CAMPUS_BRANDING } from "@/lib/theme";
import type { UserMe } from "@/lib/types";

import { LoginForm, RegisterForm } from "./forms";

export const order = 10;

type Tab = "login" | "register";

/** Only same-origin app paths; rejects //host, /\host and absolute URLs (open redirect). */
export function safeNext(next: string | null): string | null {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return null;
  return next;
}

function useDestination() {
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  return (user: UserMe) => next ?? homeFor(user);
}

function LoginPage() {
  const { status, user } = useAuth();
  // Read at render: the site brand can arrive after the first paint or change in /admin (UPS-041).
  const site = useSite();
  const [params, setParams] = useSearchParams();
  const destination = useDestination();
  const navigate = useNavigate();
  // First paint shows the form in place; switching tabs staggers the new fields in.
  const [switched, setSwitched] = useState(false);
  const tab: Tab = params.get("tab") === "registro" ? "register" : "login";

  if (status === "loading") return <PageSkeleton />;
  if (user) return <Navigate to={destination(user)} replace />;

  const onDone = (signedIn: UserMe) => navigate(destination(signedIn), { replace: true });
  const selectTab = (next: Tab) => {
    if (next === tab) return;
    setSwitched(true);
    const updated = new URLSearchParams(params);
    if (next === "register") updated.set("tab", "registro");
    else updated.delete("tab");
    setParams(updated, { replace: true });
  };
  const tabClass = (active: boolean) =>
    `min-h-11 flex-1 rounded-full text-sm font-semibold transition ${
      active ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-ink"
    }`;

  return (
    <AcademyTheme branding={CAMPUS_BRANDING} className="min-h-dvh bg-bg">
      {/* Anchored to the top with fixed padding (not centered): the card's top edge never moves when
          the tab or a message changes its height. */}
      <main className="mx-auto grid max-w-5xl items-start gap-8 px-4 pt-8 pb-10 sm:px-8 sm:pt-12 lg:grid-cols-2 lg:pt-16">
        <section className="flex flex-col items-center text-center lg:items-start lg:text-left">
          {site.logoUrl ? (
            <img src={site.logoUrl} alt={site.name} {...site.logoSize} className={`h-(--logo-h) w-auto ${LOGO_HEIGHT.login}`} />
          ) : (
            <Wordmark
              name={site.name}
              colors={{ color_primary: site.colors.primary, color_secondary: site.colors.secondary, color_accent: site.colors.accent }}
              className={`block max-w-full break-words ${LOGO_HEIGHT.login}`}
            />
          )}
          <h1 className="mt-6 text-3xl sm:text-4xl">Tus clubs en un solo campus</h1>
          <p className="mt-3 max-w-md text-muted">
            Retoma tus clases donde te quedaste y conversa con tu comunidad.
          </p>
          {site.hasMascot && (
            <img
              src={site.mascotUrl}
              alt={`Mascota de ${site.name}`}
              {...site.mascotSize}
              className="mt-6 hidden w-full max-w-xs sm:block"
            />
          )}
        </section>

        <section aria-label="Tu cuenta" className="rounded-card border border-line bg-surface p-5 shadow-soft sm:p-8">
          <div role="tablist" aria-label="Acceso" className="mb-6 flex gap-1 rounded-full bg-bg p-1">
            <button
              role="tab"
              type="button"
              aria-selected={tab === "login"}
              className={tabClass(tab === "login")}
              onClick={() => selectTab("login")}
            >
              Entrar
            </button>
            <button
              role="tab"
              type="button"
              aria-selected={tab === "register"}
              className={tabClass(tab === "register")}
              onClick={() => selectTab("register")}
            >
              Crear cuenta
            </button>
          </div>
          <AnimatedHeight>
            <div role="tabpanel" aria-label={tab === "login" ? "Entrar" : "Crear cuenta"}>
              {tab === "login" ? <LoginForm onDone={onDone} play={switched} /> : <RegisterForm onDone={onDone} play={switched} />}
            </div>
          </AnimatedHeight>
        </section>
      </main>
    </AcademyTheme>
  );
}

export const routes: RouteObject[] = [{ path: "/login", element: <LoginPage /> }];
