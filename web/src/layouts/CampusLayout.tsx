import { Article, CalendarBlank, ChatsCircle, House, ImagesSquare, UsersThree } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import { Outlet } from "react-router";

import { SITE, Wordmark } from "@/lib/brand";
import { AcademyTheme, CAMPUS_BRANDING } from "@/lib/theme";

import { ClubSwitcher } from "./ClubSwitcher";
import { Shell, type NavItem } from "./Shell";

export const CAMPUS_NAV: NavItem[] = [
  { to: "/", label: "Inicio", end: true, icon: House },
  { to: "/clubes", label: "Clubes", icon: UsersThree },
  { to: "/comunidad", label: "Comunidad", icon: ChatsCircle },
  { to: "/calendario", label: "Calendario", icon: CalendarBlank },
  { to: "/galeria", label: "Galería", icon: ImagesSquare },
  { to: "/blog", label: "Blog", icon: Article },
];

/**
 * Campus chrome (name and logo from SITE, lib/brand.tsx). Use as a layout route (`element: <CampusLayout />` + children) or wrap a page.
 * Always applies the site palette, even after visiting a club.
 */
export function CampusLayout({ children }: { children?: ReactNode }) {
  return (
    <AcademyTheme branding={CAMPUS_BRANDING}>
      <Shell
        brandTo="/"
        nav={CAMPUS_NAV}
        brand={
          SITE.logoUrl ? (
            <img src={SITE.logoUrl} alt={SITE.name} className="h-7 w-auto sm:h-8" />
          ) : (
            <Wordmark name={SITE.name} colors={CAMPUS_BRANDING} className="block min-w-0 truncate text-xl sm:text-2xl" surface="#F5F6F7" />
          )
        }
        headerSlot={<ClubSwitcher current={null} />}
      >
        {children ?? <Outlet />}
      </Shell>
    </AcademyTheme>
  );
}
