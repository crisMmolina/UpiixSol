// Academy theming (owner UPS-004): applies --academy-* CSS variables from the DB on top of the light theme.
//
//   <AcademyTheme branding={academy}>…</AcademyTheme>     // inside /a/{slug}
//   const { branding, status } = useAcademyBranding(slug); // GET /api/academies/{slug}

import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

import { api, ApiError } from "./api";
import type { AcademyBranding } from "./types";

export const CAMPUS_BRANDING: AcademyBranding = {
  slug: "upiixsol",
  name: "UpiixSol",
  logo_url: "/brand/upiixsol/wordmark.png",
  mascot_url: "/brand/upiixsol/mascot.png",
  color_primary: "#00BF63",
  color_secondary: "#04944F",
  color_accent: "#F28034",
  color_accent_2: "#B4422F",
};

const DARK_TEXT = "#1F2A24";
const LIGHT_TEXT = "#FFFFFF";

function luminance(hex: string): number {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio between two #RRGGBB colors. */
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** Dark or white text, whichever reads better on `background` (DESIGN.md: never white on #00BF63). */
export function readableTextOn(background: string): string {
  return contrastRatio(DARK_TEXT, background) >= contrastRatio(LIGHT_TEXT, background) ? DARK_TEXT : LIGHT_TEXT;
}

/** True when the best text color on `background` reaches WCAG AA for normal text (4.5:1). */
export function meetsAA(background: string): boolean {
  return contrastRatio(readableTextOn(background), background) >= 4.5;
}

export function themeVariables(branding: AcademyBranding): CSSProperties {
  const accent2 = branding.color_accent_2 ?? branding.color_secondary;
  return {
    "--academy-primary": branding.color_primary,
    "--academy-secondary": branding.color_secondary,
    "--academy-accent": branding.color_accent,
    "--academy-accent-2": accent2,
    "--academy-on-primary": readableTextOn(branding.color_primary),
    "--academy-on-accent": readableTextOn(branding.color_accent),
    "--academy-logo": branding.logo_url ? `url("${branding.logo_url}")` : "none",
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
  useEffect(() => {
    const meta = document.querySelector('meta[name="theme-color"]');
    const previous = meta?.getAttribute("content");
    meta?.setAttribute("content", branding.color_primary);
    return () => {
      if (previous) meta?.setAttribute("content", previous);
    };
  }, [branding.color_primary]);

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
