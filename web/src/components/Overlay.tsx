import { X } from "@phosphor-icons/react";
import { useEffect, useRef, type ReactNode } from "react";

/** Native <dialog> as a centered modal or a side drawer (focus trap, Esc and backdrop close for free). */
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

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      // showModal() focuses the first focusable element (the close button). Forms start at their first field.
      dialog.querySelector<HTMLElement>("input:not([type=hidden]), textarea, select")?.focus();
    }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const placement = side
    ? `m-0 h-dvh max-h-dvh w-[min(22rem,88vw)] ${side === "left" ? "mr-auto" : "ml-auto"} rounded-none`
    : "m-auto w-[min(32rem,calc(100vw-2rem))] rounded-card";

  return (
    <dialog
      ref={ref}
      aria-label={title}
      onClose={onClose}
      onClick={(event) => event.target === ref.current && onClose()}
      className={`${placement} bg-surface p-0 text-ink shadow-lift backdrop:bg-ink/40`}
    >
      <div className="flex items-center justify-between border-b border-line px-5 py-3">
        <h2 className="text-lg">{title}</h2>
        <button type="button" onClick={onClose} aria-label="Cerrar" className="grid size-11 place-items-center rounded-full hover:bg-line/60">
          <X size={20} weight="bold" />
        </button>
      </div>
      <div className="max-h-[80dvh] overflow-y-auto p-5">{children}</div>
    </dialog>
  );
}

export function Modal(props: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  return <Overlay {...props} />;
}

export function Drawer(props: { open: boolean; onClose: () => void; title: string; children: ReactNode; side?: "left" | "right" }) {
  return <Overlay side={props.side ?? "left"} {...props} />;
}
