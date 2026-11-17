import { X } from "@phosphor-icons/react";
import { motion, useReducedMotion, type Variants } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { AnimatedHeight } from "./Motion";
import { DURATION, EASE_IN, EASE_OUT } from "./motionTokens";

/** Modals hang from a fixed top instead of centering, so content that grows never moves their top edge. */
const MODAL_TOP = "max(1rem, 8dvh)";

const shownTransition = { duration: DURATION.enter, ease: EASE_OUT };
const hiddenTransition = { duration: DURATION.exit, ease: EASE_IN };
// The panel leaves a little before the backdrop fades out, so it is never on screen without it (UPS-043);
// the dialog closes when the backdrop's exit completes.
const panelHiddenTransition = { duration: DURATION.exit * 0.8, ease: EASE_IN };

const panels: Record<"modal" | "left" | "right", Variants> = {
  modal: {
    hidden: { opacity: 0, scale: 0.97, y: 8, transition: panelHiddenTransition },
    shown: { opacity: 1, scale: 1, y: 0, transition: shownTransition },
  },
  left: { hidden: { x: "-100%", transition: panelHiddenTransition }, shown: { x: 0, transition: shownTransition } },
  right: { hidden: { x: "100%", transition: panelHiddenTransition }, shown: { x: 0, transition: shownTransition } },
};
const backdrop: Variants = {
  hidden: { opacity: 0, transition: hiddenTransition },
  shown: { opacity: 1, transition: shownTransition },
};

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), ' +
  'textarea:not([disabled]), details > summary, iframe, [tabindex]:not([tabindex="-1"])';

/** Inside a closed <details> only its <summary> is reachable, yet the rest still reports layout boxes. */
function inClosedDetails(el: HTMLElement): boolean {
  const details = el.closest("details:not([open])");
  return details !== null && !(el.tagName === "SUMMARY" && el.parentElement === details);
}

/** The controls Tab can reach inside `root`, in DOM order (hidden, collapsed and inert ones left out). */
function focusStops(root: HTMLElement): HTMLElement[] {
  return [...root.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
    (el) =>
      (typeof el.checkVisibility === "function" ? el.checkVisibility() : el.getClientRects().length > 0) &&
      !inClosedDetails(el) &&
      !el.closest("[inert], [aria-hidden='true']"),
  );
}

/** Phones and tablets: focusing a text field would open the on-screen keyboard over the panel. */
function touchOrNarrow(): boolean {
  return window.matchMedia("(pointer: coarse)").matches || window.innerWidth < 640;
}

/**
 * Native <dialog> (showModal: focus trap, Esc, inert page) as a modal hanging from the top or a side
 * drawer, with enter/exit transitions. Keeps the dialog open until its exit finishes; with reduced
 * motion it opens and closes instantly. Modals focus their first field on desktop only; drawers focus
 * the close button (never a search box that would pop the phone keyboard).
 */
function Overlay({
  open,
  onClose,
  title,
  children,
  side,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  side?: "left" | "right";
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const reduce = useReducedMotion();
  // While the exit plays the parent may already have cleared what it rendered: keep the last open content.
  const [content, setContent] = useState(children);
  if (open && content !== children) setContent(children);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open) {
      if (dialog.open) return;
      dialog.showModal(); // focuses the first focusable element: the close button
      if (!side && !touchOrNarrow()) dialog.querySelector<HTMLElement>("input:not([type=hidden]), textarea, select")?.focus();
      return;
    }
    if (!dialog.open) return;
    if (reduce) {
      dialog.close();
      return;
    }
    // Normally the backdrop's exit closes it (onAnimationComplete below); this only covers a missed callback.
    const timer = window.setTimeout(() => dialog.close(), DURATION.exit * 1000 + 150);
    return () => window.clearTimeout(timer);
  }, [open, reduce, side]);

  const state = open ? "shown" : "hidden";
  const panelClass = side
    ? `absolute inset-y-0 ${side === "left" ? "left-0" : "right-0"} flex h-dvh w-[min(22rem,88vw)] flex-col`
    : "relative mx-auto flex w-[min(32rem,calc(100vw-2rem))] flex-col rounded-card";

  return (
    <dialog
      ref={ref}
      aria-label={title}
      // Esc: run the exit transition instead of the native instant close.
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
      // Tab wraps inside the dialog: a native modal still lets focus leave the page after its last control (UPS-061).
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        const stops = focusStops(event.currentTarget);
        if (stops.length === 0) return;
        const first = stops[0];
        const last = stops[stops.length - 1];
        const active = document.activeElement;
        const inside = active instanceof Node && event.currentTarget.contains(active);
        if (event.shiftKey && (active === first || !inside)) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && (active === last || !inside)) {
          event.preventDefault();
          first.focus();
        }
      }}
      // overflow-clip, not overflow-hidden: a hidden overflow is still a scroll container, and showModal focusing
      // the close button of a right drawer still off-screen (translateX(100%)) scrolled the dialog sideways, so the
      // panel showed in place before the backdrop and never slid in (UPS-043; iPhone video).
      className="m-0 size-full max-h-none max-w-none overflow-clip bg-transparent p-0 text-ink backdrop:bg-transparent"
    >
      <motion.div
        aria-hidden
        className="absolute inset-0 bg-ink/40"
        // Reduced motion: plain styles land in the same commit as the open, never one frame late.
        {...(reduce ? { style: { opacity: open ? 1 : 0 } } : { variants: backdrop, initial: "hidden", animate: state })}
        onAnimationComplete={(definition) => {
          if (definition === "hidden" && !open && ref.current?.open) ref.current.close();
        }}
        onClick={onClose}
      />
      <motion.div
        className={`${panelClass} bg-surface shadow-lift`}
        style={{
          ...(side ? {} : { marginTop: MODAL_TOP, maxHeight: `calc(100dvh - ${MODAL_TOP} - 1rem)` }),
          ...(reduce ? { opacity: open ? 1 : 0 } : {}),
        }}
        {...(reduce ? {} : { variants: panels[side ?? "modal"], initial: "hidden", animate: state })}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-line px-5 py-3">
          <h2 className="text-lg">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Cerrar" className="grid size-11 place-items-center rounded-full hover:bg-line/60">
            <X size={20} weight="bold" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {side ? (open ? children : content) : <AnimatedHeight>{open ? children : content}</AnimatedHeight>}
        </div>
      </motion.div>
    </dialog>
  );
}

/** Centered dialog hanging from the top. Content height changes animate; errors grow it downward only. */
export function Modal(props: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  return <Overlay {...props} />;
}

/** Side panel (navigation, lists). Slides in from `side` (left by default). */
export function Drawer(props: { open: boolean; onClose: () => void; title: string; children: ReactNode; side?: "left" | "right" }) {
  return <Overlay side={props.side ?? "left"} {...props} />;
}
