// Site brand (UPS-032, editable since UPS-041): the campus name, logo, mascot and palette live here and nowhere else.
//
//   SITE.name / SITE.logoUrl / SITE.mascotUrl / SITE.colors   // read during render; always the current brand
//   const site = useSite();                                    // same values, re-renders when they change
//   <Wordmark name={club.name} colors={club} className={LOGO_HEIGHT.header} />  // a name drawn like the logos
//
// Runtime store: SITE starts from the build (VITE_SITE_NAME, VITE_SITE_LOGO, the UpiixSol files in
// public/brand/) and is overwritten by GET /api/site, which superadmins edit in /admin → "Marca del sitio".
// This module waits for that read (top-level await, at most LOAD_TIMEOUT_MS; on failure the build defaults
// stay) before any importer runs, so the first paint already uses it. A later change (applySite) mutates SITE
// in place and notifies subscribers: components that read it with useSite() re-render, App.tsx keeps
// CAMPUS_BRANDING in step, and the routes remount so screens that read SITE directly render it too:
// - right away after a superadmin's save (`applySite(next, { remount: true })`);
// - on the next navigation when the first answer came late, so nothing typed on the current page is lost.
//
// Leaf module: lib/theme.tsx builds CAMPUS_BRANDING from SITE, so this file must not import theme.tsx.

import { useSyncExternalStore, type CSSProperties } from "react";

declare global {
  interface ImportMetaEnv {
    /** Default campus name until GET /api/site answers (default "UpiixSol"). */
    readonly VITE_SITE_NAME?: string;
    /** Default same-origin logo path until GET /api/site answers. Empty = no logo: the name as a wordmark. */
    readonly VITE_SITE_LOGO?: string;
  }
}

const HEX = /^#[0-9a-f]{6}$/i;
const SAME_ORIGIN_ASSET = /^\/(?!\/)[\w\-./%]+$/;

const DEFAULT_LOGO = "/brand/upiixsol/wordmark.png";
const DEFAULT_MASCOT = "/brand/upiixsol/mascot.png";
/** Stand-in for "no mascot": a 0×0 image, so `<img src={SITE.mascotUrl}>` draws nothing and takes no width. */
const NO_MASCOT = "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='0'%20height='0'/%3E";
const DEFAULT_COLORS = { primary: "#00BF63", secondary: "#04944F", accent: "#F28034" } as const;
/** How long the first paint waits for GET /api/site before using the build defaults. */
const LOAD_TIMEOUT_MS = 800;

/** GET /api/site, PUT /api/admin/site (name and colors) and the upload/remove responses. */
export interface SiteSettings {
  name: string;
  /** null → the name drawn as a three-color wordmark. */
  logo_url: string | null;
  /** null → no mascot anywhere. */
  mascot_url: string | null;
  color_primary: string;
  color_secondary: string;
  color_accent: string;
}

export interface Site {
  name: string;
  /** Browser tab title; index.html keeps the default name as its static title. */
  title: string;
  logoUrl: string | null;
  /** Intrinsic size of the logo when known (the default one), so its box is reserved before it loads. */
  logoSize?: { width: number; height: number };
  /** Always an image URL (a blank 0×0 one when the site has no mascot): check `hasMascot` to leave it out. */
  mascotUrl: string;
  hasMascot: boolean;
  mascotSize?: { width: number; height: number };
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    accent2: string;
    /** AA link shades of the primary on white and on the dark course surfaces (web/DESIGN.md). */
    link: string;
    linkDark: string;
  };
}

function safeAsset(value: string | null | undefined): string | null {
  const path = value?.trim() ?? "";
  return SAME_ORIGIN_ASSET.test(path) ? path : null;
}

function buildLogo(value: string | undefined): string | null {
  return value === undefined ? DEFAULT_LOGO : safeAsset(value);
}

/** The brand the web ships with (and keeps when GET /api/site fails or is slow). */
// oxlint-disable-next-line react/only-export-components
export const BUILT_IN_SITE: Readonly<SiteSettings> = {
  name: import.meta.env.VITE_SITE_NAME?.trim() || "UpiixSol",
  logo_url: buildLogo(import.meta.env.VITE_SITE_LOGO),
  mascot_url: DEFAULT_MASCOT,
  color_primary: DEFAULT_COLORS.primary,
  color_secondary: DEFAULT_COLORS.secondary,
  color_accent: DEFAULT_COLORS.accent,
};

function mix(hex: string, toward: number, amount: number): string {
  const channel = (i: number) => {
    const c = parseInt(hex.slice(1 + i, 3 + i), 16);
    return Math.round(c + (toward - c) * amount)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${channel(0)}${channel(2)}${channel(4)}`;
}

/** The primary, darkened (light surface) or lightened (dark surface) until text on that surface reaches AA. */
function linkShade(primary: string, surface: string, toward: number): string {
  for (let step = 0; step <= 20; step += 1) {
    const shade = mix(primary, toward, step / 20);
    if (contrastRatio(shade, surface) >= 4.5) return shade;
  }
  return toward === 0 ? "#000000" : "#FFFFFF";
}

function siteFrom(settings: SiteSettings): Site {
  const name = settings.name?.trim() || BUILT_IN_SITE.name;
  const logoUrl = safeAsset(settings.logo_url);
  const mascot = safeAsset(settings.mascot_url);
  const hex = (value: string, fallback: string) => (HEX.test(value ?? "") ? value.toUpperCase() : fallback);
  const primary = hex(settings.color_primary, DEFAULT_COLORS.primary);
  const builtInPrimary = primary === DEFAULT_COLORS.primary;
  return {
    name,
    title: `${name} Campus`,
    logoUrl,
    logoSize: logoUrl === DEFAULT_LOGO ? { width: 787, height: 211 } : undefined,
    mascotUrl: mascot ?? NO_MASCOT,
    hasMascot: mascot !== null,
    mascotSize: mascot === DEFAULT_MASCOT ? { width: 670, height: 492 } : undefined,
    colors: {
      primary,
      secondary: hex(settings.color_secondary, DEFAULT_COLORS.secondary),
      accent: hex(settings.color_accent, DEFAULT_COLORS.accent),
      accent2: "#B4422F",
      link: builtInPrimary ? "#037A41" : linkShade(primary, "#F5F6F7", 0),
      linkDark: builtInPrimary ? "#3DD68C" : linkShade(primary, "#1B1E22", 255),
    },
  };
}

/** The current site brand. Mutated in place by applySite, so read it during render, not at module load. */
// oxlint-disable-next-line react/only-export-components
export const SITE: Site = siteFrom(BUILT_IN_SITE);

function settingsOf(site: Site): SiteSettings {
  return {
    name: site.name,
    logo_url: site.logoUrl,
    mascot_url: site.hasMascot ? site.mascotUrl : null,
    color_primary: site.colors.primary,
    color_secondary: site.colors.secondary,
    color_accent: site.colors.accent,
  };
}

let current: SiteSettings = settingsOf(SITE);
let snapshot: Readonly<Site> = { ...SITE, colors: { ...SITE.colors } };
let routesVersion = 0;
/** A change arrived after the first paint (slow GET /api/site): remount the routes on the next navigation. */
let remountPending = false;
/** False until the first paint stops waiting for GET /api/site: changes before it need no remount. */
let painted = false;
const listeners = new Set<() => void>();

/** Keeps a club's tab title ("Club · Site") and the site title ("Site Campus") in step with the name. */
function retitle(previous: Site, next: Site): void {
  if (typeof document === "undefined") return;
  if (!painted || document.title === previous.title) document.title = next.title;
  else if (document.title.endsWith(` · ${previous.name}`))
    document.title = `${document.title.slice(0, -previous.name.length)}${next.name}`;
}

/**
 * Make `settings` the site brand everywhere (no-op when nothing changed). `remount` re-renders every route
 * right away (a superadmin's save); otherwise the routes remount on the next navigation.
 */
// oxlint-disable-next-line react/only-export-components
export function applySite(settings: SiteSettings, { remount = false }: { remount?: boolean } = {}): void {
  const next = siteFrom(settings);
  const normalized = settingsOf(next);
  if (JSON.stringify(normalized) === JSON.stringify(current)) return;
  current = normalized;
  const previous = { ...SITE };
  const { colors, ...rest } = next;
  Object.assign(SITE, rest);
  if (!next.logoSize) delete SITE.logoSize;
  if (!next.mascotSize) delete SITE.mascotSize;
  Object.assign(SITE.colors, colors);
  snapshot = { ...SITE, colors: { ...SITE.colors } };
  if (remount) {
    routesVersion += 1;
    remountPending = false;
  } else if (painted) {
    remountPending = true;
  }
  retitle(previous, SITE);
  for (const listener of listeners) listener();
}

/** Called by App.tsx when a navigation finishes: applies a remount left pending by a late brand. */
// oxlint-disable-next-line react/only-export-components
export function remountIfBrandChanged(): void {
  if (!remountPending) return;
  remountPending = false;
  routesVersion += 1;
  for (const listener of listeners) listener();
}

/** The site brand in the API's shape (what the /admin editor starts from). */
// oxlint-disable-next-line react/only-export-components
export function siteSettings(): SiteSettings {
  return { ...current };
}

// oxlint-disable-next-line react/only-export-components
export function subscribeSite(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The site brand; the component re-renders when a superadmin changes it. */
// oxlint-disable-next-line react/only-export-components
export function useSite(): Readonly<Site> {
  return useSyncExternalStore(subscribeSite, () => snapshot);
}

/** The key App.tsx gives the routes: it changes when they must remount to show a new brand. */
// oxlint-disable-next-line react/only-export-components
export function useRoutesKey(): number {
  return useSyncExternalStore(subscribeSite, () => routesVersion);
}

async function fetchSite(cache: RequestCache): Promise<SiteSettings> {
  const response = await fetch("/api/site", { cache, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`GET /api/site: ${response.status}`);
  return (await response.json()) as SiteSettings;
}

/**
 * Re-reads the brand past the browser cache (GET /api/site is cached for a minute), so a reload right after
 * a superadmin's change does not bring the old one back.
 */
// oxlint-disable-next-line react/only-export-components
export async function reloadSite(): Promise<void> {
  applySite(await fetchSite("reload"), { remount: true });
}

if (typeof document !== "undefined") {
  // A late answer still applies (useSite readers at once, the rest on the next navigation); a failed one
  // keeps the build defaults.
  const loading = fetchSite("default")
    .then((settings) => applySite(settings))
    .catch(() => undefined);
  await Promise.race([loading, new Promise((resolve) => setTimeout(resolve, LOAD_TIMEOUT_MS))]);
  document.title = SITE.title;
  painted = true;
}

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
