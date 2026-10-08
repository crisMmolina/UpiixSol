import { CaretUpDown, Check } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { Skeleton } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { CAMPUS_BRANDING, readableTextOn, safeAssetPath, safeColor } from "@/lib/theme";
import type { AcademyCardOut, Page } from "@/lib/types";

/** "Campus · Club X ▾": jump between the campus and any club from the top bar. */
export function ClubSwitcher({ current }: { current: string | null }) {
  const [open, setOpen] = useState(false);
  const [clubs, setClubs] = useState<AcademyCardOut[] | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    if (!clubs) {
      api<Page<AcademyCardOut>>("/academies", { query: { limit: 50 } })
        .then((page) => setClubs(page.items))
        .catch(() => setClubs([]));
    }
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !ref.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open, clubs]);

  const item = (active: boolean) =>
    `flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold text-ink no-underline transition hover:bg-subtle ${active ? "bg-subtle" : ""}`;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Cambiar de club"
        onClick={() => setOpen((value) => !value)}
        className="grid size-9 place-items-center rounded-lg text-muted transition hover:bg-line/60 hover:text-ink"
      >
        <CaretUpDown size={18} weight="bold" aria-hidden />
      </button>
      {open && (
        <div role="menu" className="animate-enter absolute left-0 z-40 mt-2 w-72 rounded-2xl border border-line bg-surface p-1.5 shadow-lift">
          <Link role="menuitem" to="/" className={item(current === null)} onClick={() => setOpen(false)}>
            <img src="/brand/upiixsol/mascot.png" alt="" className="size-8 object-contain" />
            <span className="flex-1">Campus UpiixSol</span>
            {current === null && <Check size={16} weight="bold" aria-hidden />}
          </Link>
          <p className="px-3 pb-1 pt-2 text-xs font-semibold text-muted">Clubes</p>
          {!clubs ? (
            <div className="grid gap-2 p-2">
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
            </div>
          ) : (
            clubs.map((club) => {
              const logo = safeAssetPath(club.mascot_url) ?? safeAssetPath(club.logo_url);
              return (
                <Link key={club.slug} role="menuitem" to={`/a/${club.slug}`} className={item(current === club.slug)} onClick={() => setOpen(false)}>
                  {logo ? (
                    <img src={logo} alt="" className="size-8 object-contain" />
                  ) : (
                    <span className="grid size-8 place-items-center rounded-lg text-xs font-bold" style={{ background: safeColor(club.color_primary, CAMPUS_BRANDING.color_primary), color: readableTextOn(safeColor(club.color_primary, CAMPUS_BRANDING.color_primary)) }}>
                      {club.name.slice(0, 2)}
                    </span>
                  )}
                  <span className="flex-1 truncate">{club.name}</span>
                  {current === club.slug && <Check size={16} weight="bold" aria-hidden />}
                </Link>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
