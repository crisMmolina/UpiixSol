// Site brand (UPS-032): the campus name, logo, mascot and palette live here and nowhere else.
//
//   SITE.name / SITE.logoUrl / SITE.mascotUrl / SITE.colors   // VITE_SITE_NAME, VITE_SITE_LOGO override them
//   <Wordmark name={club.name} colors={club} />                // a name drawn as a three-color logo
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

function siteLogo(value: string | undefined): string | null {
  if (value === undefined) return "/brand/upiixsol/wordmark.png";
  const path = value.trim();
  return SAME_ORIGIN_ASSET.test(path) ? path : null;
}

const siteName = import.meta.env.VITE_SITE_NAME?.trim() || "UpiixSol";

// The site config is read once at load (env vars are build-time), so fast refresh of it is irrelevant.
// oxlint-disable-next-line react/only-export-components
export const SITE = {
  name: siteName,
  /** Browser tab title; index.html keeps the default name as its static title. */
  title: `${siteName} Campus`,
  logoUrl: siteLogo(import.meta.env.VITE_SITE_LOGO),
  mascotUrl: "/brand/upiixsol/mascot.png",
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

// A brand color too light (or too dark) for the surface keeps its hue and gets a thin outline that reads.
const outline = (rgba: string) => [`1px 0 ${rgba}`, `-1px 0 ${rgba}`, `0 1px ${rgba}`, `0 -1px ${rgba}`].join(", ");
const OUTLINE_ON_LIGHT = outline("rgb(22 24 29 / 70%)");
const OUTLINE_ON_DARK = outline("rgb(255 255 255 / 80%)");

interface WordmarkColors {
  color_primary: string;
  color_secondary: string;
  color_accent: string;
}

/**
 * A club (or the campus) without a logo: its name as text in three colors. The letters before the first
 * "x" use the primary, that "x" the secondary and the rest the accent; with no "x" (or an "x" first) the
 * whole name uses the primary. "UpiixRobótica" → "Upii" · "x" · "Robótica".
 * Exposed as one image named after the club (logotype), like the logo it replaces. A color under 3:1 against
 * `surface` gets a thin outline so the name stays legible. Layout (block, truncate, line clamp, width) comes
 * from `className`; the base only sets the type.
 */
export function Wordmark({
  name,
  colors,
  className = "",
  surface = "#FFFFFF",
}: {
  name: string;
  colors: WordmarkColors;
  className?: string;
  /** Background the wordmark sits on (#RRGGBB), to decide when a color needs the outline. */
  surface?: string;
}) {
  const x = name.search(/x/i);
  const [head, mark, tail] = x > 0 ? [name.slice(0, x), name[x], name.slice(x + 1)] : [name, "", ""];
  const style = (value: string, fallback: string) => {
    const color = HEX.test(value) ? value : fallback;
    const outline = contrastRatio(color, surface) < 3 ? (luminance(surface) > 0.18 ? OUTLINE_ON_LIGHT : OUTLINE_ON_DARK) : undefined;
    return { color, textShadow: outline };
  };
  return (
    <span role="img" aria-label={name} data-wordmark="" className={`font-display font-bold leading-tight tracking-tight ${className}`}>
      <span aria-hidden style={style(colors.color_primary, SITE.colors.primary)}>
        {head}
      </span>
      {mark && (
        <span aria-hidden style={style(colors.color_secondary, SITE.colors.secondary)}>
          {mark}
        </span>
      )}
      {tail && (
        <span aria-hidden style={style(colors.color_accent, SITE.colors.accent)}>
          {tail}
        </span>
      )}
    </span>
  );
}
