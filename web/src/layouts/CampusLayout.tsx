import type { ReactNode } from "react";
import { Outlet } from "react-router";

import { AcademyTheme, CAMPUS_BRANDING } from "@/lib/theme";

import { Shell, type NavItem } from "./Shell";

export const CAMPUS_NAV: NavItem[] = [
  { to: "/", label: "Inicio", end: true },
  { to: "/academias", label: "Academias" },
  { to: "/comunidad", label: "Comunidad" },
  { to: "/calendario", label: "Calendario" },
  { to: "/galeria", label: "Galería" },
  { to: "/blog", label: "Blog" },
];

/**
 * UpiixSol campus chrome. Use as a layout route (`element: <CampusLayout />` + children) or wrap a page.
 * Always applies the UpiixSol palette, even after visiting an academy.
 */
export function CampusLayout({ children }: { children?: ReactNode }) {
  return (
    <AcademyTheme branding={CAMPUS_BRANDING}>
      <Shell
        brandTo="/"
        nav={CAMPUS_NAV}
        brand={<img src="/brand/upiixsol/wordmark.png" alt="UpiixSol" className="h-8 w-auto sm:h-10" />}
      >
        {children ?? <Outlet />}
      </Shell>
    </AcademyTheme>
  );
}
