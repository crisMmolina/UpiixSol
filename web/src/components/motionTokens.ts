// Motion tokens (web/DESIGN.md · Movimiento y estabilidad). Same curve as the CSS `.enter` animation.

type Bezier = [number, number, number, number];

/** Entering and resizing: quick start, soft landing. */
export const EASE_OUT: Bezier = [0.2, 0.8, 0.2, 1];
/** Leaving: accelerates out of view. */
export const EASE_IN: Bezier = [0.4, 0, 1, 1];

/** Seconds. `exit` is shorter than `enter`: closing should never make anyone wait. */
export const DURATION = {
  /** Messages fading in or out. */
  fast: 0.16,
  /** Overlays and fields entering. */
  enter: 0.22,
  /** Overlays leaving. */
  exit: 0.16,
  /** Containers growing or shrinking. */
  height: 0.26,
  /** Delay between staggered items. */
  stagger: 0.04,
} as const;
