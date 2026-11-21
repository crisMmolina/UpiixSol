// In-place text on the email canvas (spec 005 §Canvas): an auto-growing textarea styled like the email text, with
// the formatted text (the renderer's `**negritas**`, `*cursivas*`, `[texto](url)`) shown while the block is not
// being edited. The textarea is always mounted (invisible underneath the formatted text when inactive), so it
// keeps its label, value and Tab stop; clicking the formatted text focuses it. No rich-text dependency.
import { useLayoutEffect, type CSSProperties, type KeyboardEvent, type ReactNode, type RefObject } from "react";

import { isHttpUrl } from "./blocks";

// The server's patterns (app/services/mail_render.py `_LINK`, `_BOLD`, `_ITALIC`).
const LINK = /\[([^[\]]{1,300})\]\(((?:[^()\s]|\([^()\s]*\)){1,2000})\)/g;
const BOLD = /\*\*(.+?)\*\*/g;
const ITALIC = /\*(.+?)\*/g;

function split(text: string, pattern: RegExp, wrap: (match: RegExpMatchArray, key: string) => ReactNode, rest: (part: string, key: string) => ReactNode, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    const at = match.index ?? 0;
    if (at > last) out.push(rest(text.slice(last, at), `${key}r${last}`));
    out.push(wrap(match, `${key}m${at}`));
    last = at + match[0].length;
  }
  if (last < text.length) out.push(rest(text.slice(last), `${key}r${last}`));
  return out;
}

function italics(text: string, key: string): ReactNode[] {
  return split(text, ITALIC, (m, k) => <em key={k}>{m[1]}</em>, (part) => part, key);
}

function emphasis(text: string, key: string): ReactNode[] {
  return split(text, BOLD, (m, k) => <strong key={k}>{italics(m[1], k)}</strong>, (part, k) => italics(part, k), key);
}

/** The formatted text, as the email shows it. A link the server would refuse keeps only its label. */
export function Formatted({ text, linkColor }: { text: string; linkColor: string }) {
  return (
    <>
      {split(
        text,
        LINK,
        (m, k) =>
          isHttpUrl(m[2]) ? (
            <a key={k} href={m[2]} tabIndex={-1} onClick={(e) => e.preventDefault()} style={{ color: linkColor, textDecoration: "underline", fontWeight: 600 }}>
              {emphasis(m[1], k)}
            </a>
          ) : (
            <span key={k}>{emphasis(m[1], k)}</span>
          ),
        (part, k) => emphasis(part, k),
        "f",
      )}
    </>
  );
}

export interface Edit {
  value: string;
  start: number;
  end: number;
}

/** Wraps the selection with `before`/`after` (or inserts a sample word, selected, when nothing is selected). */
export function wrapSelection(value: string, start: number, end: number, before: string, after: string, sample = "texto"): Edit {
  const picked = value.slice(start, end) || sample;
  const next = value.slice(0, start) + before + picked + after + value.slice(end);
  return { value: next, start: start + before.length, end: start + before.length + picked.length };
}

/** Turns the selection into `[selección](url)`; the caret lands after the link. */
export function insertLink(value: string, start: number, end: number, url: string): Edit {
  const label = value.slice(start, end).replace(/[[\]]/g, "") || "enlace";
  const link = `[${label}](${url.trim()})`;
  const next = value.slice(0, start) + link + value.slice(end);
  return { value: next, start: start + link.length, end: start + link.length };
}

export function InlineText({
  inputRef,
  label,
  value,
  onChange,
  active,
  placeholder,
  maxLength,
  singleLine,
  textStyle,
  view,
  describedBy,
  onKeyDown,
}: {
  inputRef: RefObject<HTMLTextAreaElement | null>;
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** The block is selected: the raw text is edited; otherwise the formatted `view` shows. */
  active: boolean;
  placeholder: string;
  maxLength?: number;
  /** Headings: no line breaks. */
  singleLine?: boolean;
  textStyle: CSSProperties;
  view: ReactNode;
  describedBy?: string;
  onKeyDown?: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
}) {
  // Auto-grow: as tall as its text while it is edited.
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    if (!active) {
      el.style.height = "";
      return;
    }
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [active, value, inputRef]);

  function focusAtEnd(event: { preventDefault: () => void }) {
    event.preventDefault();
    const el = inputRef.current;
    if (!el) return;
    el.focus();
    el.setSelectionRange(el.value.length, el.value.length);
  }

  return (
    <div className="relative">
      {!active && (
        <div aria-hidden onMouseDown={focusAtEnd} className="relative z-[1] cursor-text break-words whitespace-pre-wrap" style={textStyle}>
          {value.trim() ? view : <span style={{ opacity: 0.45 }}>{placeholder}</span>}
        </div>
      )}
      <textarea
        ref={inputRef}
        aria-label={label}
        aria-describedby={describedBy}
        value={value}
        rows={1}
        maxLength={maxLength}
        placeholder={placeholder}
        spellCheck
        onChange={(e) => onChange(singleLine ? e.target.value.replace(/[\r\n]+/g, " ") : e.target.value)}
        onKeyDown={onKeyDown}
        style={textStyle}
        className={`block w-full resize-none overflow-hidden border-0 bg-transparent p-0 outline-none placeholder:opacity-45 ${active ? "" : "absolute inset-0 h-full opacity-0"}`}
      />
    </div>
  );
}
