import { DotsThreeOutline, type Icon } from "@phosphor-icons/react";
import { useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router";

import { Drawer } from "@/components/Overlay";

import { NotificationBell, Toasts } from "./Notifications";
import { UserMenu } from "./UserMenu";

export interface NavItem {
  to: string;
  label: string;
  end?: boolean;
  icon?: Icon;
}

/**
 * App chrome for campus and club layouts (reference: course campus with an icon rail).
 * Desktop: left icon rail + slim top bar + white content panel. Phone: top bar + bottom tab bar.
 * No footer: this is an app, not a website.
 */
export function Shell({
  brand,
  brandTo,
  nav,
  railTop,
  headerSlot,
  children,
}: {
  brand: ReactNode;
  brandTo: string;
  nav: NavItem[];
  /** Pinned first rail entry (e.g. the way back to the campus from a club). */
  railTop?: NavItem;
  /** Extra controls next to the brand (e.g. the club switcher). */
  headerSlot?: ReactNode;
  children: ReactNode;
}) {
  const [moreOpen, setMoreOpen] = useState(false);
  // Phones: up to 5 tabs; with more items the last tab is "Más" and opens the rest in a drawer.
  const all = railTop ? [railTop, ...nav] : nav;
  const tabs = all.length > 5 ? all.slice(0, 4) : all;
  const rest = all.length > 5 ? all.slice(4) : [];

  return (
    <div className="min-h-dvh bg-subtle">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-surface focus:px-4 focus:py-2"
      >
        Saltar al contenido
      </a>

      <aside aria-label="Navegación" className="fixed inset-y-0 left-0 z-30 hidden w-[5.5rem] flex-col items-center gap-1 overflow-y-auto py-3 lg:flex">
        {railTop && (
          <>
            <RailLink item={railTop} />
            <hr className="my-1 w-10 border-line" />
          </>
        )}
        <nav aria-label="Principal" className="flex flex-col items-center gap-1">
          {nav.map((item) => (
            <RailLink key={item.to} item={item} />
          ))}
        </nav>
      </aside>

      <div className="lg:pl-[5.5rem]">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 bg-subtle/90 px-4 backdrop-blur sm:px-6">
          <Link to={brandTo} className="flex shrink-0 items-center no-underline">
            {brand}
          </Link>
          {headerSlot}
          <div className="ml-auto flex items-center gap-1">
            <NotificationBell />
            <UserMenu />
          </div>
        </header>

        <main
          id="contenido"
          className="min-h-[calc(100dvh-4rem)] border-line bg-bg pb-24 lg:rounded-tl-2xl lg:border-l lg:border-t lg:pb-0"
        >
          <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-8 sm:py-8">{children}</div>
        </main>
      </div>

      <nav
        aria-label="Principal móvil"
        className="fixed inset-x-0 bottom-0 z-30 flex border-t border-line bg-surface/95 px-1 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
      >
        {tabs.map((item) => (
          <TabLink key={item.to} item={item} />
        ))}
        {rest.length > 0 && (
          <button type="button" onClick={() => setMoreOpen(true)} className={tabClass(false)}>
            <DotsThreeOutline size={22} weight="bold" aria-hidden />
            Más
          </button>
        )}
      </nav>
      <Drawer open={moreOpen} onClose={() => setMoreOpen(false)} title="Más" side="right">
        <div className="grid gap-1">
          {rest.map((item) => {
            const IconComponent = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setMoreOpen(false)}
                className={({ isActive }) =>
                  `flex min-h-12 items-center gap-3 rounded-xl px-3 font-semibold no-underline ${isActive ? "bg-subtle text-ink" : "text-muted hover:bg-subtle hover:text-ink"}`
                }
              >
                {IconComponent && <IconComponent size={22} aria-hidden />}
                {item.label}
              </NavLink>
            );
          })}
        </div>
      </Drawer>

      <Toasts />
    </div>
  );
}

function RailLink({ item }: { item: NavItem }) {
  const IconComponent = item.icon;
  return (
    <NavLink to={item.to} end={item.end} className="group flex w-20 flex-col items-center gap-1 py-1.5 text-[0.7rem] font-medium no-underline">
      {({ isActive }) => (
        <>
          <span
            className={`grid size-10 place-items-center rounded-xl transition duration-200 ${
              isActive ? "bg-surface text-ink shadow-soft ring-1 ring-line" : "text-muted group-hover:bg-line/60 group-hover:text-ink"
            }`}
          >
            {IconComponent && <IconComponent size={22} weight={isActive ? "fill" : "regular"} aria-hidden />}
          </span>
          <span className={isActive ? "text-ink" : "text-muted group-hover:text-ink"}>{item.label}</span>
        </>
      )}
    </NavLink>
  );
}

const tabClass = (active: boolean) =>
  `flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[0.7rem] font-medium no-underline ${active ? "text-ink" : "text-muted"}`;

function TabLink({ item }: { item: NavItem }) {
  const IconComponent = item.icon;
  return (
    <NavLink to={item.to} end={item.end} className={({ isActive }) => tabClass(isActive)}>
      {({ isActive }) => (
        <>
          {IconComponent && <IconComponent size={22} weight={isActive ? "fill" : "regular"} aria-hidden />}
          <span className="max-w-full truncate px-1">{item.label}</span>
        </>
      )}
    </NavLink>
  );
}
