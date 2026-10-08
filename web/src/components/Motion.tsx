import { motion, useReducedMotion, type Variants } from "motion/react";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

import { DURATION, EASE_OUT } from "./motionTokens";

/**
 * Animates its own height whenever the content's height changes (tab switch, a message appearing).
 * Measures with ResizeObserver; with reduced motion the height switches instantly.
 * The content gets a 4 px bleed so focus rings are not clipped while it animates. Do not put floating
 * menus inside: the container clips (overflow hidden).
 */
export function AnimatedHeight({ children, className = "" }: { children: ReactNode; className?: string }) {
  const inner = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | "auto">("auto");
  const reduce = useReducedMotion();

  useLayoutEffect(() => {
    const element = inner.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) =>
      setHeight(entry.borderBoxSize?.[0]?.blockSize ?? element.getBoundingClientRect().height),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <motion.div
      className={`-m-1 overflow-hidden ${className}`}
      initial={false}
      animate={{ height }}
      transition={reduce ? { duration: 0 } : { duration: DURATION.height, ease: EASE_OUT }}
    >
      <div ref={inner} className="p-1">
        {children}
      </div>
    </motion.div>
  );
}

const group: Variants = { hidden: {}, shown: { transition: { staggerChildren: DURATION.stagger } } };
const item: Variants = {
  hidden: { opacity: 0, y: 6 },
  shown: { opacity: 1, y: 0, transition: { duration: DURATION.enter, ease: EASE_OUT } },
};
const still: Variants = { hidden: { opacity: 1 }, shown: { opacity: 1 } };

/**
 * Children marked with <StaggerItem> fade and rise in one after another (40 ms apart).
 * `play={false}` renders them in place (first paint of a screen should not animate; a switch should).
 */
export function Stagger({ children, className = "", play = true }: { children: ReactNode; className?: string; play?: boolean }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} variants={reduce ? undefined : group} initial={play && !reduce ? "hidden" : false} animate="shown">
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className = "" }: { children: ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} variants={reduce ? still : item}>
      {children}
    </motion.div>
  );
}
