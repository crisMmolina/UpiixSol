import DOMPurify from "dompurify";
import { marked } from "marked";
import { useMemo } from "react";

marked.setOptions({ gfm: true, breaks: true });

// External links open in a new tab, safely. The hook is added only around our own sanitize call,
// so other DOMPurify users in the app are not affected.
function externalLinks(node: Element): void {
  if (node.tagName === "A" && /^https?:/i.test(node.getAttribute("href") ?? "")) {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer nofollow");
  }
}

function sanitize(html: string): string {
  DOMPurify.addHook("afterSanitizeAttributes", externalLinks);
  try {
    return DOMPurify.sanitize(html, {
      USE_PROFILES: { html: true },
      FORBID_TAGS: ["style", "iframe", "form", "input", "img"],
      // http(s), mailto, in-page anchors and same-origin paths (not //host or /\\host, which browsers treat as external).
      ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|#|\/(?![/\\]))/i,
    });
  } finally {
    DOMPurify.removeHook("afterSanitizeAttributes", externalLinks);
  }
}

/** Renders sanitized markdown (server already cleans with nh3; DOMPurify is the second layer). */
export function Markdown({ source, className = "" }: { source: string; className?: string }) {
  const html = useMemo(() => sanitize(marked.parse(source, { async: false })), [source]);
  // eslint-disable-next-line react/no-danger -- sanitized above
  return <div className={`prose-campus ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}
