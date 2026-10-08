import { X } from "@phosphor-icons/react";
import { motion, useReducedMotion, type Variants } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { AnimatedHeight } from "./Motion";
import { DURATION, EASE_IN, EASE_OUT } from "./motionTokens";

/** Modals hang from a fixed top instead of centering, so content that grows never moves their top edge. */
const MODAL_TOP = "max(1rem, 8dvh)";

const shownTransition = { duration: DURATION.enter, ease: EASE_OUT };
const hiddenTransition = { duration: DURATION.exit, ease: EASE_IN };

const panels: Record<"modal" | "left" | "right", Variants> = {
  modal: {
    hidden: { opacity: 0, scale: 0.97, y: 8, transition: hiddenTransition },
    shown: { opacity: 1, scale: 1, y: 0, transition: shownTransition },
  },
  left: { hidden: { x: "-100%", transition: hiddenTransition }, shown: { x: 0, transition: shownTransition } },
  right: { hidden: { x: "100%", transition: hiddenTransition }, shown: { x: 0, transition: shownTransition } },
};
const backdrop: Variants = {
  hidden: { opacity: 0, transition: hiddenTransition },
  shown: { opacity: 1, transition: shownTransition },
};
const instant: Variants = { hidden: { opacity: 0, transition: { duration: 0 } }, shown: { opacity: 1, transition: { duration: 0 } } };

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
    const timer = window.setTimeout(() => dialog.close(), DURATION.exit * 1000);
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
      className="m-0 size-full max-h-none max-w-none overflow-hidden bg-transparent p-0 text-ink backdrop:bg-transparent"
    >
      <motion.div
        aria-hidden
        className="absolute inset-0 bg-ink/40"
        variants={reduce ? instant : backdrop}
        initial="hidden"
        animate={state}
        onClick={onClose}
      />
      <motion.div
        className={`${panelClass} bg-surface shadow-lift`}
        style={side ? undefined : { marginTop: MODAL_TOP, maxHeight: `calc(100dvh - ${MODAL_TOP} - 1rem)` }}
        variants={reduce ? instant : panels[side ?? "modal"]}
        initial="hidden"
        animate={state}
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
