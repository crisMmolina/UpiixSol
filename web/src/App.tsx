import type { ComponentType, ReactNode } from "react";
import { createBrowserRouter, RouterProvider, type RouteObject } from "react-router";

// Contract (owner UPS-001, nobody edits this file after setup):
// - Each feature is web/src/features/<name>/index.tsx and exports `routes: RouteObject[]`
//   (optionally `order`; lower orders are matched first). Features wrap their own layouts.
// - Root providers (auth, theme...) live in web/src/lib/providers.tsx with a default export
//   `({ children }) => ...` (owner UPS-004). If it does not exist yet, the app still builds.
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
      <h1 className="text-3xl font-bold">UpiixSol Campus</h1>
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
const router = createBrowserRouter([
  ...featureRoutes,
  ...(hasRoot ? [] : [{ path: "/", element: <Placeholder /> }]),
  { path: "*", element: <NotFound /> },
]);

export default function App() {
  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}
