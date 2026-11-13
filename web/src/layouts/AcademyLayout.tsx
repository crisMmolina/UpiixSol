import { ArrowUUpLeft, CalendarBlank, ChatsCircle, FolderOpen, House, Path } from "@phosphor-icons/react";
import { createContext, use, useEffect, type ReactNode } from "react";
import { Link, Outlet, useParams } from "react-router";

import { PageSkeleton } from "@/components/Skeleton";
import { EmptyState, ErrorState } from "@/components/States";
import { ApiError, errorMessage } from "@/lib/api";
import { LOGO_HEIGHT, SITE, Wordmark } from "@/lib/brand";
import { AcademyTheme, safeAssetPath, useAcademyBranding } from "@/lib/theme";
import type { AcademyBranding } from "@/lib/types";

import { CampusLayout } from "./CampusLayout";
import { ClubSwitcher } from "./ClubSwitcher";
import { Shell, type NavItem } from "./Shell";

const AcademyContext = createContext<AcademyBranding | null>(null);

/** Branding of the club in the URL; available to every page under /a/:slug. */
export function useAcademy(): AcademyBranding {
  const academy = use(AcademyContext);
  if (!academy) throw new Error("useAcademy must be used inside <AcademyLayout>");
  return academy;
}

export function academyNav(slug: string): NavItem[] {
  return [
    { to: `/a/${slug}`, label: "Inicio", end: true, icon: House },
    { to: `/a/${slug}/rutas`, label: "Rutas", icon: Path },
    { to: `/a/${slug}/recursos`, label: "Recursos", icon: FolderOpen },
    { to: `/a/${slug}/comunidad`, label: "Comunidad", icon: ChatsCircle },
    { to: `/a/${slug}/eventos`, label: "Eventos", icon: CalendarBlank },
  ];
}

const CAMPUS_LINK: NavItem = { to: "/", label: "Campus", end: true, icon: ArrowUUpLeft };

/**
 * Layout route for `/a/:slug/*`: loads the club branding, re-themes the whole page with its
 * colors and logo, and exposes it through `useAcademy()`. The rail switches to the club's sections,
 * with "Campus" pinned on top as the way back.
 */
export function AcademyLayout({ children }: { children?: ReactNode }) {
  const { slug } = useParams<{ slug: string }>();
  const { status, branding, error, retry } = useAcademyBranding(slug);
  const clubName = branding?.name;

  // Tab title: "Club · Campus"; back to the site title when leaving the club.
  useEffect(() => {
    if (!clubName) return;
    document.title = `${clubName} · ${SITE.name}`;
    return () => {
      document.title = SITE.title;
    };
  }, [clubName]);

  if (status === "loading") return <PageSkeleton />;
  if (status === "error") {
    return (
      <CampusLayout>
        {error instanceof ApiError && error.status === 404 ? (
          <EmptyState
            title="Este club no existe o ya no está activo"
            description="Revisa el enlace o explora los clubes del campus."
            action={<Link to="/clubes">Ver clubes</Link>}
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
          railTop={CAMPUS_LINK}
          headerSlot={<ClubSwitcher current={branding.slug} />}
          brand={
            safeAssetPath(branding.logo_url) ? (
              <img src={safeAssetPath(branding.logo_url)!} alt={branding.name} className={`h-(--logo-h) w-auto min-w-[calc(var(--logo-h)*3.75)] object-contain object-left ${LOGO_HEIGHT.header}`} />
            ) : (
              <Wordmark name={branding.name} colors={branding} className={`block min-w-0 truncate ${LOGO_HEIGHT.header}`} />
            )
          }
        >
          {children ?? <Outlet />}
        </Shell>
      </AcademyContext>
    </AcademyTheme>
  );
}
