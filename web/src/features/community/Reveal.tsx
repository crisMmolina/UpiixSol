// Height reveal for optional rows of the composer (UPS-035).
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

import { DURATION, EASE_IN, EASE_OUT } from "@/components";

/**
 * Optional content that grows and shrinks its own height (and fades) instead of pushing what follows
 * at once. Put spacing inside the child (e.g. `pt-3`), never as a parent gap, so nothing jumps at the end.
 */
export function Reveal({ show, children }: { show: boolean; children: ReactNode }) {
  const reduce = useReducedMotion();
  const enter = reduce ? { duration: 0 } : { duration: DURATION.height, ease: EASE_OUT };
  const leave = reduce ? { duration: 0 } : { duration: DURATION.exit, ease: EASE_IN };
  return (
    <AnimatePresence initial={false}>
      {show && (
        <motion.div
          className="-mx-1 overflow-y-clip px-1"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1, transition: enter }}
          exit={{ height: 0, opacity: 0, transition: leave }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
