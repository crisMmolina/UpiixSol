// Academy theming (owner UPS-004): applies --academy-* CSS variables from the DB on top of the light theme.
//
//   <AcademyTheme branding={academy}>…</AcademyTheme>     // inside /a/{slug}
//   const { branding, status } = useAcademyBranding(slug); // GET /api/academies/{slug}

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

import { api, ApiError } from "./api";
import { contrastRatio, SITE } from "./brand";
import type { AcademyBranding } from "./types";

/** The campus as a "club": name, logo and palette from the site brand (lib/brand.tsx). */
export const CAMPUS_BRANDING: AcademyBranding = {
  slug: "campus",
  name: SITE.name,
  logo_url: SITE.logoUrl,
  mascot_url: SITE.mascotUrl,
  color_primary: SITE.colors.primary,
  color_secondary: SITE.colors.secondary,
  color_accent: SITE.colors.accent,
  color_accent_2: SITE.colors.accent2,
};

export { contrastRatio };

const DARK_TEXT = "#1F2A24";
const LIGHT_TEXT = "#FFFFFF";

/** Dark or white text, whichever reads better on `background` (DESIGN.md: never white on #00BF63). */
export function readableTextOn(background: string): string {
  return contrastRatio(DARK_TEXT, background) >= contrastRatio(LIGHT_TEXT, background) ? DARK_TEXT : LIGHT_TEXT;
}

/** True when the best text color on `background` reaches WCAG AA for normal text (4.5:1). */
export function meetsAA(background: string): boolean {
  return contrastRatio(readableTextOn(background), background) >= 4.5;
}

function mix(hex: string, toward: number, amount: number): string {
  const value = hex.replace("#", "");
  const channel = (i: number) => {
    const c = parseInt(value.slice(i, i + 2), 16);
    return Math.round(c + (toward - c) * amount)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${channel(0)}${channel(2)}${channel(4)}`;
}

/** The club primary, darkened (light surfaces) or lightened (dark surfaces) until text reaches AA. */
function linkShade(primary: string, surface: string, toward: number): string {
  for (let step = 0; step <= 20; step += 1) {
    const shade = mix(primary, toward, step / 20);
    if (contrastRatio(shade, surface) >= 4.5) return shade;
  }
  return toward === 0 ? "#000000" : "#FFFFFF";
}

const HEX = /^#[0-9a-f]{6}$/i;
const ASSET_PATH = /^\/(?!\/)[\w\-./%]+$/;

/** Second layer over the API's validation: only #RRGGBB reaches CSS, else the campus color. */
export function safeColor(value: string | null | undefined, fallback: string): string {
  return value && HEX.test(value) ? value : fallback;
}

/** Only same-origin asset paths (/brand/..., /media/...) are used as images or CSS urls. */
export function safeAssetPath(value: string | null | undefined): string | null {
  return value && ASSET_PATH.test(value) ? value : null;
}

export function themeVariables(branding: AcademyBranding): CSSProperties {
  const primary = safeColor(branding.color_primary, CAMPUS_BRANDING.color_primary);
  const secondary = safeColor(branding.color_secondary, CAMPUS_BRANDING.color_secondary);
  const accent = safeColor(branding.color_accent, CAMPUS_BRANDING.color_accent);
  const logo = safeAssetPath(branding.logo_url);
  const campus = primary.toUpperCase() === SITE.colors.primary;
  return {
    "--academy-primary": primary,
    "--academy-secondary": secondary,
    "--academy-accent": accent,
    // Every accent-2 consumer is an alert (errors, invalid fields, delete buttons): a club without its own
    // falls back to the site's alert red, never to its secondary color (UPS-064: green read as success).
    "--academy-accent-2": safeColor(branding.color_accent_2, SITE.colors.accent2),
    "--academy-on-primary": readableTextOn(primary),
    "--academy-on-accent": readableTextOn(accent),
    // Links (index.css picks the shade for the surface): the campus keeps its tuned greens.
    "--academy-link-light": campus ? SITE.colors.link : linkShade(primary, "#F5F6F7", 0),
    "--academy-link-dark": campus ? SITE.colors.linkDark : linkShade(primary, "#1B1E22", 255),
    "--academy-logo": logo ? `url("${logo}")` : "none",
  } as CSSProperties;
}

export function AcademyTheme({
  branding,
  children,
  className = "",
}: {
  branding: AcademyBranding;
  children: ReactNode;
  className?: string;
}) {
  // Keep the browser chrome (mobile address bar) in the academy color too.
  const primary = safeColor(branding.color_primary, CAMPUS_BRANDING.color_primary);
  useEffect(() => {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) return;
    const previous = meta.getAttribute("content");
    meta.setAttribute("content", primary);
    return () => {
      if (previous) meta.setAttribute("content", previous);
      else meta.removeAttribute("content");
    };
  }, [primary]);

  return (
    <div data-academy-theme={branding.slug} style={themeVariables(branding)} className={className}>
      {children}
    </div>
  );
}

type BrandingState =
  | { status: "loading"; branding: null; error: null }
  | { status: "ready"; branding: AcademyBranding; error: null }
  | { status: "error"; branding: null; error: ApiError | Error };

const LOADING: BrandingState = { status: "loading", branding: null, error: null };

export function useAcademyBranding(slug: string | undefined): BrandingState & { retry: () => void } {
  // The result is keyed by `slug:attempt`, so a new slug (or a retry) reads as loading during render.
  const [result, setResult] = useState<{ key: string; state: BrandingState } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const key = `${slug}:${attempt}`;

  useEffect(() => {
    if (!slug) return;
    let active = true;
    api<AcademyBranding>(`/academies/${encodeURIComponent(slug)}`)
      .then((branding) => active && setResult({ key, state: { status: "ready", branding, error: null } }))
      .catch((error: Error) => active && setResult({ key, state: { status: "error", branding: null, error } }));
    return () => {
      active = false;
    };
  }, [slug, key]);

  const state = result?.key === key ? result.state : LOADING;
  return { ...state, retry: () => setAttempt((n) => n + 1) };
}
