// Site brand (UPS-032): the campus name, logo, mascot and palette live here and nowhere else.
//
//   SITE.name / SITE.logoUrl / SITE.mascotUrl / SITE.colors   // VITE_SITE_NAME, VITE_SITE_LOGO override them
//   <Wordmark name={club.name} colors={club} className={LOGO_HEIGHT.header} />  // a name drawn like the logos
//
// Leaf module: lib/theme.tsx builds CAMPUS_BRANDING from SITE, so this file must not import theme.tsx.

import type { CSSProperties } from "react";

declare global {
  interface ImportMetaEnv {
    /** Campus name shown in the header, the switcher and the tab title (default "UpiixSol"). */
    readonly VITE_SITE_NAME?: string;
    /** Same-origin path of the campus logo (e.g. /brand/x/logo.png). Empty = no logo: the name as a wordmark. */
    readonly VITE_SITE_LOGO?: string;
  }
}

const HEX = /^#[0-9a-f]{6}$/i;
const SAME_ORIGIN_ASSET = /^\/(?!\/)[\w\-./%]+$/;

const DEFAULT_LOGO = "/brand/upiixsol/wordmark.png";

function siteLogo(value: string | undefined): string | null {
  if (value === undefined) return DEFAULT_LOGO;
  const path = value.trim();
  return SAME_ORIGIN_ASSET.test(path) ? path : null;
}

const siteName = import.meta.env.VITE_SITE_NAME?.trim() || "UpiixSol";
const logoUrl = siteLogo(import.meta.env.VITE_SITE_LOGO);

// The site config is read once at load (env vars are build-time), so fast refresh of it is irrelevant.
// oxlint-disable-next-line react/only-export-components
export const SITE = {
  name: siteName,
  /** Browser tab title; index.html keeps the default name as its static title. */
  title: `${siteName} Campus`,
  logoUrl,
  /** Intrinsic size of the logo when known (the default one), so its box is reserved before it loads. */
  logoSize: logoUrl === DEFAULT_LOGO ? { width: 787, height: 211 } : undefined,
  mascotUrl: "/brand/upiixsol/mascot.png",
  mascotSize: { width: 670, height: 492 },
  colors: {
    primary: "#00BF63",
    secondary: "#04944F",
    accent: "#F28034",
    accent2: "#B4422F",
    /** AA link shades of the primary on white and on the dark course surfaces (web/DESIGN.md). */
    link: "#037A41",
    linkDark: "#3DD68C",
  },
} as const;

if (typeof document !== "undefined") document.title = SITE.title;

function luminance(hex: string): number {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio between two #RRGGBB colors (re-exported by lib/theme.tsx). */
// oxlint-disable-next-line react/only-export-components
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Height of the logo in each place it shows, as the CSS variable --logo-h. The <img> and the <Wordmark> that
// replaces it take the same entry (`h-(--logo-h)` / `max-h-(--logo-h)` on the image), so they cannot drift.
// oxlint-disable-next-line react/only-export-components
export const LOGO_HEIGHT = {
  /** Top bar (campus and club). */
  header: "[--logo-h:1.75rem] sm:[--logo-h:2rem]",
  /** Club card band in /clubes and the campus home. */
  card: "[--logo-h:3.5rem]",
  /** "Mis clubs" continue tile. */
  tile: "[--logo-h:2rem]",
  /** Login screen. */
  login: "[--logo-h:3rem] sm:[--logo-h:3.5rem]",
  /** Club switcher rows (no logo image there: the name sits beside the club's icon). */
  menu: "[--logo-h:1.25rem]",
} as const;

// The logo images (public/brand/*/wordmark.png) are Fredoka 700 with 0.01 em of extra spacing, and their
// height is the ink from the "i" dot to the "p" tail: 0.949 em. So a wordmark for a --logo-h tall logo uses
// font-size --logo-h / 0.949. Its line box is 1.2 --logo-h (two lines never touch) with -0.1 --logo-h
// margins, so a single line takes exactly the logo's box; Fredoka's ink sits 0.1155 em below the middle of
// the line box, so the whole name (ellipsis included) is lifted by that much. Checked side by side against
// the logos in e2e/test_wordmark.py.
const LOGO_H = "var(--logo-h, 1.75rem)";
const LOGO_BOX: CSSProperties = {
  fontSize: `calc(${LOGO_H} / 0.949)`,
  lineHeight: `calc(${LOGO_H} * 1.2)`,
  marginBlock: `calc(${LOGO_H} * -0.1)`,
  position: "relative",
  top: "-0.1155em",
};

interface WordmarkColors {
  color_primary: string;
  color_secondary: string;
  color_accent: string;
}

/**
 * A club (or the campus) without a logo: its name drawn like the logo images (Fredoka bold, lowercase, the
 * font's own tight spacing, one baseline) in three plain colors, with no outline. The letters before the
 * first "x" use the primary, that "x" the secondary and the rest the accent; with no "x" (or an "x" first)
 * the whole name uses the primary. Before the "x" and the "x" itself are shown lowercase, the rest keeps its
 * case: "UpiixRobótica" → "upii" · "x" · "Robótica" (CSS only, so the text keeps the stored case).
 * Exposed as one image named after the club (logotype), like the logo it replaces. Its size is the logo's
 * height: pass the same LOGO_HEIGHT entry the <img> uses in `className`, with the layout (block, truncate,
 * line clamp, width).
 */
export function Wordmark({
  name,
  colors,
  className = "",
}: {
  name: string;
  colors: WordmarkColors;
  className?: string;
}) {
  const x = name.search(/x/i);
  const [head, mark, tail] = x > 0 ? [name.slice(0, x), name[x], name.slice(x + 1)] : [name, "", ""];
  const color = (value: string, fallback: string) => (HEX.test(value) ? value : fallback);
  const piece = (value: string, fallback: string, lower: boolean) => ({
    color: color(value, fallback),
    textTransform: lower ? ("lowercase" as const) : undefined,
  });
  // The truncation ellipsis is drawn by the outer span: give it the color of the last piece.
  const last = tail ? color(colors.color_accent, SITE.colors.accent) : color(colors.color_primary, SITE.colors.primary);
  return (
    <span
      role="img"
      aria-label={name}
      data-wordmark=""
      style={{ ...LOGO_BOX, color: last }}
      className={`font-display font-bold tracking-[0.01em] ${className}`}
    >
      <span aria-hidden style={piece(colors.color_primary, SITE.colors.primary, x > 0)}>
        {head}
      </span>
      {mark && (
        <span aria-hidden style={piece(colors.color_secondary, SITE.colors.secondary, true)}>
          {mark}
        </span>
      )}
      {tail && (
        <span aria-hidden style={piece(colors.color_accent, SITE.colors.accent, false)}>
          {tail}
        </span>
      )}
    </span>
  );
}
