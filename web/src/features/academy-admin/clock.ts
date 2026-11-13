/** Segment clock text ↔ seconds (UPS-048). Pure: no React, no DOM. */

const CLOCK = /^(?:(\d+):)?(\d{1,2}):(\d{2})$/;

/** "14:10" → 850, "1:02:03" → 3723; anything else (or minutes/seconds ≥ 60) → null. */
export function parseClock(text: string): number | null {
  const match = CLOCK.exec(text.trim());
  if (!match) return null;
  const [, h, m, s] = match;
  const hours = h ? Number(h) : 0;
  const minutes = Number(m);
  const seconds = Number(s);
  if (seconds >= 60 || (h && minutes >= 60)) return null;
  return hours * 3600 + minutes * 60 + seconds;
}

/** 850 → "14:10", 3723 → "1:02:03". */
export function formatClock(total: number): string {
  const t = Math.max(0, Math.floor(total));
  const hours = Math.floor(t / 3600);
  const minutes = Math.floor((t % 3600) / 60);
  const seconds = String(t % 60).padStart(2, "0");
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${seconds}` : `${minutes}:${seconds}`;
}

const OFFSET = /^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$/;

/** The start a YouTube URL carries in `t` or `start` (query or hash): "850", "850s", "14m10s", "1h2m3s". */
export function startFromUrl(url: string): number | null {
  let parsed: URL;
  try {
    parsed = new URL(url.trim());
  } catch {
    return null;
  }
  const hash = new URLSearchParams(parsed.hash.replace(/^#/, ""));
  const raw = parsed.searchParams.get("t") ?? parsed.searchParams.get("start") ?? hash.get("t") ?? hash.get("start");
  const match = raw ? OFFSET.exec(raw) : null;
  if (!match || !match[0]) return null;
  const [, h, m, s] = match;
  const seconds = Number(h ?? 0) * 3600 + Number(m ?? 0) * 60 + Number(s ?? 0);
  return seconds > 0 ? seconds : null;
}
