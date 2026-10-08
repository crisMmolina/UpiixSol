// Layouts (owner UPS-021). Typical feature routes:
//
//   export const routes: RouteObject[] = [
//     { element: <CampusLayout />, children: [{ path: "/comunidad", element: <Community /> }] },
//     { path: "/a/:slug", element: <AcademyLayout />, children: [{ index: true, element: <AcademyHome /> }] },
//   ];
//   Protected pages: wrap the element in <RequireRole roles={["superadmin"]}> (from @/lib/auth).
export { AcademyLayout, academyNav, useAcademy } from "./AcademyLayout";
export { CAMPUS_NAV, CampusLayout } from "./CampusLayout";
export { Shell, type NavItem } from "./Shell";
