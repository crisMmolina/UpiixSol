// UPS-019: drag-and-drop ordering with native HTML5 DnD (no dependency). Each list is a "group"
// (e.g. the modules of one route): items only drop within their own group, because the reorder
// endpoints order siblings. Native DnD has no touch or keyboard support; the arrow buttons stay
// as the accessible fallback.
import { useState, type DragEvent } from "react";

type Key = { group: string; id: number };

/** New order after dropping `from` on `to`: it takes `to`'s place (after it when moving down). */
export function reorderIds(ids: number[], from: number, to: number): number[] {
  const next = ids.filter((id) => id !== from);
  next.splice(ids.indexOf(to), 0, from);
  return next;
}

export function useSortable() {
  const [dragging, setDragging] = useState<Key | null>(null);
  const [over, setOver] = useState<Key | null>(null);

  const reset = () => {
    setDragging(null);
    setOver(null);
  };

  /** Props for one draggable item of `group`; `ids` is the group's current order. */
  function item(group: string, ids: number[], id: number, onReorder: (ids: number[]) => void) {
    const mine = dragging?.group === group;
    return {
      draggable: true,
      "data-dragging": (mine && dragging?.id === id) || undefined,
      "data-over": (mine && over?.group === group && over.id === id && dragging?.id !== id) || undefined,
      onDragStart(event: DragEvent<HTMLElement>) {
        event.stopPropagation(); // a lesson inside a draggable module drags only itself
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(id)); // Firefox needs data to start a drag
        setDragging({ group, id });
      },
      onDragOver(event: DragEvent<HTMLElement>) {
        if (!mine) return; // another group: let it bubble to an outer list (e.g. the module)
        event.preventDefault();
        event.stopPropagation();
        event.dataTransfer.dropEffect = "move";
        if (over?.group !== group || over.id !== id) setOver({ group, id });
      },
      onDrop(event: DragEvent<HTMLElement>) {
        if (!mine || !dragging) return;
        event.preventDefault();
        event.stopPropagation();
        const from = dragging.id;
        reset();
        if (from !== id) onReorder(reorderIds(ids, from, id));
      },
      onDragEnd: reset,
    };
  }

  return { item };
}
