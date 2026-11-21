// Small things the composer's steps share.
import type { Dispatch } from "react";

import type { ComposerAction, ComposerState } from "./composerState";

export const MAX_SUBJECT = 150;
export const MAX_PREHEADER = 140;
export const BOARD = "La mesa directiva de UpiixSol";

export interface StepProps {
  state: ComposerState;
  dispatch: Dispatch<ComposerAction>;
  /** Slug of the club the "Ver el club" button preset links to; null while none applies. */
  clubSlug: string | null;
  /** Slug that limits the campus-event picker; null = every club's events; undefined = not known yet. */
  eventsAcademy: string | null | undefined;
  /** What the exact preview renders; null while there is nothing to show. */
  previewPayload: object | null;
  onBack: () => void;
}

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

/** "1 de diciembre": the period end is a UTC midnight, so read it in UTC. */
export function renewal(iso: string) {
  const d = new Date(iso);
  return `${d.getUTCDate()} de ${MESES[d.getUTCMonth()]}`;
}

export function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}
