// A picker in the menu style of "Agregar destinatarios" (AudienceSources.tsx): a field-like button that opens a
// rounded card of options, the current one marked with a check. Replaces the native <select> in the composer.
import { CaretDown, Check } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

export interface MenuOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export function MenuSelect({
  label,
  value,
  options,
  onChange,
  placeholder = "Elige una opción",
}: {
  label: string;
  value: string;
  options: MenuOption[];
  onChange: (value: string) => void;
  /** Shown on the button while `value` matches no option. */
  placeholder?: string;
}) {
  const id = useId();
  const labelId = `${id}-label`;
  const listId = `${id}-list`;
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const current = options.find((o) => o.value === value);

  const nodes = () => [...(root.current?.querySelectorAll<HTMLButtonElement>("[role=option]:not([disabled])") ?? [])];

  useEffect(() => {
    if (!open) return;
    const all = nodes();
    (all.find((n) => n.getAttribute("aria-selected") === "true") ?? all[0])?.focus({ preventScroll: true });
    list.current?.scrollIntoView({ block: "nearest" }); // scroll-mb keeps it clear of the phone's bottom bar
    const away = (event: PointerEvent) => !root.current?.contains(event.target as Node) && setOpen(false);
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  function close(refocus: boolean) {
    setOpen(false);
    if (refocus) trigger.current?.focus();
  }

  function onTriggerKey(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
    }
  }

  function onListKey(event: KeyboardEvent<HTMLDivElement>) {
    const all = nodes();
    const at = all.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      all[(at + (event.key === "ArrowDown" ? 1 : -1) + all.length) % all.length]?.focus();
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      (event.key === "Home" ? all[0] : all[all.length - 1])?.focus();
    } else if (event.key === "Tab") {
      close(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <label id={labelId} htmlFor={id} className="text-sm font-semibold text-ink">
        {label}
      </label>
      <div ref={root} className="relative">
        <button
          ref={trigger}
          id={id}
          type="button"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={open ? listId : undefined}
          onClick={() => setOpen((v) => !v)}
          onKeyDown={onTriggerKey}
          className="flex min-h-11 w-full items-center justify-between gap-3 rounded-[var(--radius-field)] border border-line bg-surface px-3.5 py-2.5 text-left text-ink shadow-xs focus:border-secondary focus:outline-none focus:ring-3 focus:ring-primary/25"
        >
          <span className={`min-w-0 truncate ${current ? "" : "text-muted"}`}>{current?.label ?? placeholder}</span>
          <CaretDown size={14} weight="bold" aria-hidden className={`shrink-0 motion-safe:transition-transform ${open ? "rotate-180" : ""}`} />
        </button>
        {open && (
          <div
            ref={list}
            id={listId}
            role="listbox"
            aria-labelledby={labelId}
            onKeyDown={onListKey}
            className="absolute left-0 z-30 mt-2 grid max-h-72 scroll-mb-24 w-full gap-0.5 overflow-y-auto rounded-2xl border border-line bg-surface p-2 text-ink shadow-lift"
          >
            {options.map((o) => (
              <button
                key={o.value}
                type="button"
                role="option"
                aria-selected={o.value === value}
                disabled={o.disabled}
                tabIndex={-1}
                onClick={() => {
                  close(true);
                  onChange(o.value);
                }}
                className={`flex min-h-11 items-center justify-between gap-3 rounded-xl px-3 text-left text-sm font-semibold hover:bg-subtle focus-visible:bg-subtle focus-visible:outline-3 disabled:text-muted disabled:hover:bg-transparent ${o.value === value ? "bg-subtle" : ""}`}
              >
                <span className="min-w-0">{o.label}</span>
                {o.value === value && <Check size={16} weight="bold" aria-hidden className="shrink-0 text-secondary" />}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
