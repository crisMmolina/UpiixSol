import { useEffect, type ComponentType, type ReactNode } from "react";
import { createBrowserRouter, matchRoutes, Outlet, RouterProvider, useLocation, type RouteObject } from "react-router";

import { setAnalyticsUser, track } from "./lib/analytics";
import { useAuth } from "./lib/auth";
import { SITE, subscribeSite, useSiteVersion } from "./lib/brand";
import { CAMPUS_BRANDING } from "./lib/theme";

// Contract (owner UPS-001, nobody edits this file after setup):
// - Each feature is web/src/features/<name>/index.tsx and exports `routes: RouteObject[]`
//   (optionally `order`; lower orders are matched first). Features wrap their own layouts.
// - Root providers (auth, theme...) live in web/src/lib/providers.tsx with a default export
//   `({ children }) => ...` (owner UPS-004). If it does not exist yet, the app still builds.
// - Every route renders inside <PageViews>, which records a `page.view` usage event per navigation with the
//   route template ("/a/:slug/clases/:lessonId"), never the raw URL (UPS-037, web/src/lib/analytics.ts).
//   It reads the session from AuthProvider (web/src/lib/providers.tsx).
// - Site brand (UPS-041): lib/brand.tsx has already loaded GET /api/site before this module runs (top-level
//   await, ≤ 800 ms, build defaults on failure), so the first paint uses it. When it changes later (a
//   superadmin saves "Marca del sitio" in /admin, or a slow first answer), CAMPUS_BRANDING follows and the
//   routes remount under the new brand; the providers (session, notifications) stay mounted.
type FeatureModule = { routes?: RouteObject[]; order?: number };
type ProvidersModule = { default: ComponentType<{ children: ReactNode }> };

const featureRoutes = Object.values(
  import.meta.glob<FeatureModule>("./features/*/index.tsx", { eager: true }),
)
  .sort((a, b) => (a.order ?? 100) - (b.order ?? 100))
  .flatMap((feature) => feature.routes ?? []);

const Providers =
  Object.values(import.meta.glob<ProvidersModule>("./lib/providers.tsx", { eager: true }))[0]?.default ??
  (({ children }: { children: ReactNode }) => <>{children}</>);

function Placeholder() {
  return (
    <main className="grid min-h-dvh place-items-center bg-[#FBF8EF] p-4 text-[#1F2A24]">
      <h1 className="text-3xl font-bold">{SITE.title}</h1>
    </main>
  );
}

function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center bg-[#FBF8EF] p-4 text-center text-[#1F2A24]">
      <div>
        <h1 className="text-3xl font-bold">Página no encontrada</h1>
        <a className="mt-4 inline-block font-semibold text-[#04944F] underline" href="/">
          Volver al inicio
        </a>
      </div>
    </main>
  );
}

const hasRoot = featureRoutes.some((route) => route.path === "/" || route.index);
const appRoutes: RouteObject[] = [
  ...featureRoutes,
  ...(hasRoot ? [] : [{ path: "/", element: <Placeholder /> }]),
  { path: "*", element: <NotFound /> },
];

/** "/a/upiixia/clases/12" → { path: "/a/:slug/clases/:lessonId", slug: "upiixia" } (club slug only under /a/). */
function pageOf(pathname: string): { path: string; academySlug?: string } {
  let path = "";
  for (const { route } of matchRoutes(appRoutes, pathname) ?? []) {
    if (!route.path) continue;
    path = route.path.startsWith("/") ? route.path : `${path.replace(/\/$/, "")}/${route.path}`;
  }
  const slug = /^\/a\/([a-z0-9-]+)/.exec(pathname)?.[1];
  return { path: path || "/", academySlug: path.startsWith("/a/:slug") ? slug : undefined };
}

function PageViews() {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const userId = user?.id ?? null;

  useEffect(() => setAnalyticsUser(userId), [userId]);
  useEffect(() => {
    if (userId === null) return;
    const { path, academySlug } = pageOf(pathname);
    track("page.view", { path, academy_slug: academySlug });
  }, [pathname, userId]);

  return <Outlet />;
}

// lib/theme.tsx copies SITE into CAMPUS_BRANDING when it loads: keep that copy in step with later changes.
subscribeSite(() =>
  Object.assign(CAMPUS_BRANDING, {
    name: SITE.name,
    logo_url: SITE.logoUrl,
    mascot_url: SITE.hasMascot ? SITE.mascotUrl : null,
    color_primary: SITE.colors.primary,
    color_secondary: SITE.colors.secondary,
    color_accent: SITE.colors.accent,
  }),
);

const router = createBrowserRouter([{ element: <PageViews />, children: appRoutes }]);

export default function App() {
  // Screens read SITE while rendering: a new key re-renders all of them with the new brand (same URL).
  const brand = useSiteVersion();
  return (
    <Providers>
      <RouterProvider key={brand} router={router} />
    </Providers>
  );
}
