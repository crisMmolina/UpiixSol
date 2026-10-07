import { List } from "@phosphor-icons/react";
import { useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router";

import { Drawer } from "@/components/Overlay";
import { Notice } from "@/components/States";
import { useAuth } from "@/lib/auth";

import { UserMenu } from "./UserMenu";

export interface NavItem {
  to: string;
  label: string;
  end?: boolean;
}

/** Shared chrome for campus and academy layouts: sticky header, desktop nav, mobile drawer, footer. */
export function Shell({
  brand,
  brandTo,
  nav,
  topSlot,
  children,
}: {
  brand: ReactNode;
  brandTo: string;
  nav: NavItem[];
  topSlot?: ReactNode;
  children: ReactNode;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user } = useAuth();
  const location = useLocation();

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex min-h-11 items-center rounded-full px-3.5 text-[0.95rem] font-semibold no-underline transition ${
      isActive ? "bg-primary/15 text-ink ring-1 ring-primary/40" : "text-muted hover:bg-line/50 hover:text-ink"
    }`;

  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-surface focus:px-4 focus:py-2">
        Saltar al contenido
      </a>
      <header className="sticky top-0 z-20 border-b border-line bg-surface/90 backdrop-blur">
        {topSlot}
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-8">
          <button
            type="button"
            className="grid size-11 place-items-center rounded-full hover:bg-line/50 lg:hidden"
            aria-label="Abrir menú"
            onClick={() => setMenuOpen(true)}
          >
            <List size={24} weight="bold" />
          </button>
          <Link to={brandTo} className="flex shrink-0 items-center no-underline">
            {brand}
          </Link>
          <nav aria-label="Principal" className="ml-4 hidden flex-1 items-center gap-1 lg:flex">
            {nav.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto">
            <UserMenu />
          </div>
        </div>
      </header>

      <Drawer open={menuOpen} onClose={() => setMenuOpen(false)} title="Menú">
        <nav aria-label="Principal móvil" className="flex flex-col gap-1">
          {nav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass} onClick={() => setMenuOpen(false)}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </Drawer>

      {user?.must_change_password && location.pathname !== "/cuenta" && (
        <div className="mx-auto w-full max-w-6xl px-4 pt-4 sm:px-8">
          <Notice action={<Link to="/cuenta" className="font-semibold">Ir a Mi cuenta →</Link>}>
            Estás usando una contraseña provisional. Cámbiala junto con tu correo en Mi cuenta → Seguridad.
          </Notice>
        </div>
      )}

      <main id="contenido" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-8 sm:py-10">
        {children}
      </main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-6 text-sm text-muted sm:px-8">
          <span>UpiixSol Campus · Tu club, tus academias, un solo campus</span>
          <span>IPN · UPIIZ</span>
        </div>
      </footer>
    </div>
  );
}
