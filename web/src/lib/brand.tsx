// Site brand (UPS-032): the campus name, logo, mascot and palette live here and nowhere else.
//
//   SITE.name / SITE.logoUrl / SITE.mascotUrl / SITE.colors   // VITE_SITE_NAME, VITE_SITE_LOGO override them
//   <Wordmark name={club.name} colors={club} />                // a name drawn like the logo images, in three colors
//
// Leaf module: lib/theme.tsx builds CAMPUS_BRANDING from SITE, so this file must not import theme.tsx.

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

// The logo images (public/brand/*/wordmark.png) are Fredoka 700 at its own spacing, and an image `h-N` is
// 0.949 em tall (the "i" dot to the "p" tail). Callers size a wordmark like plain text: the header uses
// `text-xl sm:text-2xl` where a logo is `h-7 sm:h-8`, so the letters are drawn 1.475 em (phone) and 1.405 em
// (sm and up) of that size, the x-height of the image (checked side by side in e2e/test_wordmark.py). The
// images space the letters 0.01 em wider than the font does. Fredoka's ink (i dot to p tail) sits 0.115 em
// below the middle of its line box: lifting it centers the letters where a logo image would be centered.
const LOGO_TYPE = "relative -top-[0.115em] text-[1.475em] tracking-[0.01em] sm:text-[1.405em]";

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
 * Exposed as one image named after the club (logotype), like the logo it replaces. Layout (block, truncate,
 * line clamp, width) and the base size come from `className`; the letters are drawn larger (LOGO_TYPE).
 */
export function Wordmark({
  name,
  colors,
  className = "",
}: {
  name: string;
  colors: WordmarkColors;
  className?: string;
  /** No longer used (the outline is gone); kept so callers that still pass it compile. */
  surface?: string;
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
      style={{ color: last }}
      className={`font-display font-bold leading-tight tracking-normal ${className}`}
    >
      <span aria-hidden className={LOGO_TYPE} style={piece(colors.color_primary, SITE.colors.primary, x > 0)}>
        {head}
      </span>
      {mark && (
        <span aria-hidden className={LOGO_TYPE} style={piece(colors.color_secondary, SITE.colors.secondary, true)}>
          {mark}
        </span>
      )}
      {tail && (
        <span aria-hidden className={LOGO_TYPE} style={piece(colors.color_accent, SITE.colors.accent, false)}>
          {tail}
        </span>
      )}
    </span>
  );
}
