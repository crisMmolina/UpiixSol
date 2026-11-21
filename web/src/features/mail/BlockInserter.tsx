// "+" on the canvas (spec 005 §Canvas): a menu of the seven block kinds (icon, name, one-line description).
// Keyboard: the first item takes focus, ↑/↓ move, Esc closes and returns focus to "+", Tab closes.
import { CalendarBlank, CursorClick, Image as ImageIcon, ListBullets, Minus, Plus, TextAlignLeft, TextHOne, type Icon } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { KINDS, type DraftKind } from "./blocks";

const ICONS: Record<DraftKind, Icon> = {
  heading: TextHOne,
  paragraph: TextAlignLeft,
  list: ListBullets,
  button: CursorClick,
  event: CalendarBlank,
  image: ImageIcon,
  divider: Minus,
};

export function BlockInserter({
  label,
  onPick,
  disabled,
  eventTaken,
  variant,
}: {
  /** Accessible name of the "+" button. */
  label: string;
  onPick: (kind: DraftKind) => void;
  disabled: boolean;
  /** The email already has its one event. */
  eventTaken: boolean;
  /** `between`: a small round "+" on the seam between two blocks; `end`: the wide "Agregar bloque" row. */
  variant: "between" | "end";
}) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLButtonElement>("[role=menuitem]:not(:disabled)")?.focus();
    const away = (event: PointerEvent) => !root.current?.contains(event.target as Node) && setOpen(false);
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  function close(refocus: boolean) {
    setOpen(false);
    if (refocus) trigger.current?.focus();
  }

  function onMenuKey(event: KeyboardEvent<HTMLDivElement>) {
    const items = [...(root.current?.querySelectorAll<HTMLButtonElement>("[role=menuitem]:not(:disabled)") ?? [])];
    const at = items.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      items[(at + step + items.length) % items.length]?.focus();
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      items[event.key === "Home" ? 0 : items.length - 1]?.focus();
    } else if (event.key === "Tab") {
      close(false);
    }
  }

  const button =
    variant === "end"
      ? `flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed text-sm font-semibold motion-safe:transition focus-visible:outline-3 disabled:cursor-not-allowed disabled:opacity-50 ${open ? "border-primary text-ink" : "border-line text-muted hover:border-primary hover:text-ink"}`
      : `grid size-8 place-items-center rounded-full border-2 bg-surface shadow-soft motion-safe:transition focus-visible:outline-3 disabled:hidden ${open ? "border-primary bg-primary text-on-primary" : "border-line text-muted hover:border-primary hover:text-ink"}`;

  return (
    <div ref={root} className="relative">
      <button
        ref={trigger}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className={button}
      >
        <Plus weight="bold" size={variant === "end" ? 16 : 14} />
        {variant === "end" && <span aria-hidden>Agregar bloque</span>}
      </button>
      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label="Tipo de bloque"
          onKeyDown={onMenuKey}
          className={`absolute z-30 mt-2 w-[min(19rem,calc(100vw-3rem))] rounded-2xl border border-line bg-surface p-2 text-ink shadow-lift ${variant === "end" ? "left-1/2 -translate-x-1/2" : "left-1/2 -translate-x-1/2"}`}
        >
          {KINDS.map(({ kind, label: name, hint }) => {
            const Icon = ICONS[kind];
            const off = kind === "event" && eventTaken;
            const hintId = `${menuId}-${kind}`;
            return (
              <button
                key={kind}
                type="button"
                role="menuitem"
                aria-label={name}
                aria-describedby={hintId}
                disabled={off}
                onClick={() => {
                  setOpen(false);
                  onPick(kind);
                }}
                className="flex w-full items-center gap-3 rounded-xl px-2 py-1.5 text-left hover:bg-subtle focus-visible:bg-subtle focus-visible:outline-3 disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:bg-transparent"
              >
                <span aria-hidden className="grid size-9 shrink-0 place-items-center rounded-lg bg-subtle text-ink">
                  <Icon weight="bold" size={18} />
                </span>
                <span className="grid min-w-0">
                  <span className="text-sm font-semibold">{name}</span>
                  <span id={hintId} className="text-xs text-muted">
                    {off ? "Un correo lleva un solo evento" : hint}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
