import { CheckCircle, WarningCircle } from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { DURATION, EASE_OUT } from "./motionTokens";

export type MessageTone = "error" | "success" | "info";

const toneClass: Record<MessageTone, string> = {
  error: "font-semibold text-accent-2",
  success: "font-semibold text-link",
  info: "text-muted",
};

/**
 * A message line that always keeps its space: showing, swapping or hiding a message never moves the
 * layout. Use it under a field (size "xs") or under a submit button for the form-level error or result.
 *
 * - `message` (error/success/info by `tone`) is announced through an aria-live region and fades in/out.
 * - `hint` shows (muted, not announced) while there is no message: e.g. why a button is disabled.
 * - `lines` is the space kept (1 by default). Keep messages short enough to fit it; a longer one still
 *   shows, it just grows the slot.
 */
export function FormMessage({
  id,
  message,
  tone = "error",
  hint,
  lines = 1,
  size = "sm",
  live = true,
  className = "",
}: {
  id?: string;
  message?: string | null;
  tone?: MessageTone;
  hint?: string | null;
  lines?: number;
  size?: "xs" | "sm";
  /** Field messages are read through aria-describedby instead. */
  live?: boolean;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const fade = reduce ? { duration: 0 } : { duration: DURATION.fast, ease: EASE_OUT };
  const lineHeight = size === "xs" ? 1 : 1.25; // rem: leading-4 / leading-5
  const text = size === "xs" ? "text-xs leading-4" : "text-sm leading-5";
  const Icon = tone === "error" ? WarningCircle : tone === "success" ? CheckCircle : null;
  const showHint = Boolean(hint) && !message;

  return (
    <div id={id} className={`grid ${text} ${className}`} style={{ minHeight: `${lines * lineHeight}rem` }}>
      <p role={live ? "status" : undefined} className="grid [grid-area:1/1]">
        <AnimatePresence initial={false}>
          {message && (
            <motion.span
              key={`${tone}:${message}`}
              className={`flex items-start gap-1.5 [grid-area:1/1] ${toneClass[tone]}`}
              initial={{ opacity: 0, y: reduce ? 0 : -2 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={fade}
            >
              {Icon && size === "sm" && <Icon size={16} weight="bold" aria-hidden className="mt-0.5 shrink-0" />}
              <span>{message}</span>
            </motion.span>
          )}
        </AnimatePresence>
      </p>
      <AnimatePresence initial={false}>
        {showHint && (
          <motion.span
            key="hint"
            className="text-muted [grid-area:1/1]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={fade}
          >
            {hint}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}
