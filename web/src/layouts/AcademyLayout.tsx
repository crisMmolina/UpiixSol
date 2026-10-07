import { ArrowLeft } from "@phosphor-icons/react";
import { createContext, use, type ReactNode } from "react";
import { Link, Outlet, useParams } from "react-router";

import { PageSkeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { ApiError, errorMessage } from "@/lib/api";
import { AcademyTheme, useAcademyBranding } from "@/lib/theme";
import type { AcademyBranding } from "@/lib/types";

import { CampusLayout } from "./CampusLayout";
import { Shell, type NavItem } from "./Shell";

const AcademyContext = createContext<AcademyBranding | null>(null);

/** Branding of the academy in the URL; available to every page under /a/:slug. */
export function useAcademy(): AcademyBranding {
  const academy = use(AcademyContext);
  if (!academy) throw new Error("useAcademy must be used inside <AcademyLayout>");
  return academy;
}

export function academyNav(slug: string): NavItem[] {
  return [
    { to: `/a/${slug}`, label: "Inicio", end: true },
    { to: `/a/${slug}/rutas`, label: "Rutas" },
    { to: `/a/${slug}/recursos`, label: "Recursos" },
    { to: `/comunidad?canal=${slug}`, label: "Comunidad" },
    { to: `/a/${slug}/eventos`, label: "Eventos" },
  ];
}

/**
 * Layout route for `/a/:slug/*`: loads the academy branding, re-themes the whole page with its
 * colors and logo, and exposes it through `useAcademy()`.
 */
export function AcademyLayout({ children }: { children?: ReactNode }) {
  const { slug } = useParams<{ slug: string }>();
  const { status, branding, error, retry } = useAcademyBranding(slug);

  if (status === "loading") return <PageSkeleton />;
  if (status === "error") {
    return (
      <CampusLayout>
        {error instanceof ApiError && error.status === 404 ? (
          <EmptyState
            title="Esta academia no existe o ya no está activa"
            description="Revisa el enlace o explora las academias del club."
            action={<Link to="/academias">Ver academias</Link>}
          />
        ) : (
          <ErrorState message={errorMessage(error)} onRetry={retry} />
        )}
      </CampusLayout>
    );
  }

  return (
    <AcademyTheme branding={branding}>
      <AcademyContext value={branding}>
        <Shell
          brandTo={`/a/${branding.slug}`}
          nav={academyNav(branding.slug)}
          topSlot={
            <div className="bg-primary/10 text-sm">
              <div className="mx-auto flex h-9 max-w-6xl items-center px-4 sm:px-8">
                <Link to="/" className="inline-flex items-center gap-1.5 font-semibold no-underline">
                  <ArrowLeft size={14} weight="bold" aria-hidden /> Campus UpiixSol
                </Link>
              </div>
            </div>
          }
          brand={
            branding.logo_url ? (
              <img src={branding.logo_url} alt={branding.name} className="h-8 w-auto sm:h-10" />
            ) : (
              <span className="font-display text-2xl font-bold text-ink">{branding.name}</span>
            )
          }
        >
          {children ?? <Outlet />}
        </Shell>
      </AcademyContext>
    </AcademyTheme>
  );
}
