import { Article, CalendarBlank, ChatsCircle, House, ImagesSquare, UsersThree } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import { Outlet } from "react-router";

import { AcademyTheme, CAMPUS_BRANDING } from "@/lib/theme";

import { ClubSwitcher } from "./ClubSwitcher";
import { Shell, type NavItem } from "./Shell";

export const CAMPUS_NAV: NavItem[] = [
  { to: "/", label: "Inicio", end: true, icon: House },
  { to: "/academias", label: "Clubes", icon: UsersThree },
  { to: "/comunidad", label: "Comunidad", icon: ChatsCircle },
  { to: "/calendario", label: "Calendario", icon: CalendarBlank },
  { to: "/galeria", label: "Galería", icon: ImagesSquare },
  { to: "/blog", label: "Blog", icon: Article },
];

/**
 * UpiixSol campus chrome. Use as a layout route (`element: <CampusLayout />` + children) or wrap a page.
 * Always applies the UpiixSol palette, even after visiting a club.
 */
export function CampusLayout({ children }: { children?: ReactNode }) {
  return (
    <AcademyTheme branding={CAMPUS_BRANDING}>
      <Shell
        brandTo="/"
        nav={CAMPUS_NAV}
        brand={<img src="/brand/upiixsol/wordmark.png" alt="UpiixSol" className="h-7 w-auto sm:h-8" />}
        headerSlot={<ClubSwitcher current={null} />}
      >
        {children ?? <Outlet />}
      </Shell>
    </AcademyTheme>
  );
}
