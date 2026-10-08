import { CaretUpDown, Check } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import { Skeleton } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { SITE, Wordmark } from "@/lib/brand";
import { CAMPUS_BRANDING, readableTextOn, safeAssetPath, safeColor } from "@/lib/theme";
import type { AcademyCardOut, Page } from "@/lib/types";

/**
 * Two letters that tell clubs apart: the first letter plus the one after the first "x" ("UpiixRobótica" → UR);
 * else the initials of the first two words ("AUD Robots" → AR), else the first two letters.
 */
function clubInitials(name: string): string {
  const letters = (text: string) => text.match(/[\p{L}\p{N}]/gu) ?? [];
  const first = letters(name)[0] ?? "?";
  const x = name.search(/x/i);
  const afterX = x > 0 ? letters(name.slice(x + 1))[0] : undefined;
  if (afterX) return (first + afterX).toUpperCase();
  const words = name.split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  if (words.length > 1) return (words[0][0] + words[1][0]).toUpperCase();
  return letters(name).slice(0, 2).join("").toUpperCase() || first;
}

/** Initials per club, unique within the list: on a clash, the first letter + the next unused letter. */
function initialsFor(clubs: AcademyCardOut[]): Map<string, string> {
  const used = new Set<string>();
  const result = new Map<string, string>();
  for (const club of clubs) {
    let initials = clubInitials(club.name);
    if (used.has(initials)) {
      const letters = (club.name.match(/[\p{L}\p{N}]/gu) ?? []).map((c) => c.toUpperCase());
      initials = letters.slice(1).map((c) => letters[0] + c).find((pair) => !used.has(pair)) ?? initials;
    }
    used.add(initials);
    result.set(club.slug, initials);
  }
  return result;
}

/** Fallback tile for a club without logo or mascot: its initials on its primary color. */
function ClubInitials({ club, initials }: { club: AcademyCardOut; initials: string }) {
  const primary = safeColor(club.color_primary, CAMPUS_BRANDING.color_primary);
  return (
    <span
      aria-hidden
      className="grid size-8 shrink-0 place-items-center rounded-lg font-display text-sm font-bold"
      style={{ background: primary, color: readableTextOn(primary), boxShadow: `inset 0 -3px 0 ${safeColor(club.color_accent, primary)}` }}
    >
      {initials}
    </span>
  );
}

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

  const initials = clubs ? initialsFor(clubs) : null;
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
        className="grid size-11 place-items-center rounded-xl text-muted transition hover:bg-line/60 hover:text-ink"
      >
        <CaretUpDown size={18} weight="bold" aria-hidden />
      </button>
      {open && (
        <div role="menu" className="animate-enter fixed inset-x-4 top-16 z-40 rounded-2xl sm:absolute sm:inset-x-auto sm:left-0 sm:top-auto sm:mt-2 sm:w-72 border border-line bg-surface p-1.5 shadow-lift">
          <Link role="menuitem" to="/" className={item(current === null)} onClick={() => setOpen(false)}>
            <img src={SITE.mascotUrl} alt="" className="size-8 object-contain" />
            <span className="flex-1">Campus {SITE.name}</span>
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
                  {logo ? <img src={logo} alt="" className="size-8 shrink-0 object-contain" /> : <ClubInitials club={club} initials={initials?.get(club.slug) ?? clubInitials(club.name)} />}
                  {logo ? (
                    <span className="flex-1 truncate">{club.name}</span>
                  ) : (
                    <span className="min-w-0 flex-1">
                      <Wordmark name={club.name} colors={club} className="text-base" />
                    </span>
                  )}
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
