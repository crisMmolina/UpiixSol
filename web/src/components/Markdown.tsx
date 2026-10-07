import DOMPurify from "dompurify";
import { marked } from "marked";
import { useMemo } from "react";

marked.setOptions({ gfm: true, breaks: true });

// Links open in a new tab, safely. Hook registered once at module load.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A") {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer nofollow");
  }
});

/** Renders sanitized markdown (server already cleans with nh3; DOMPurify is the second layer). */
export function Markdown({ source, className = "" }: { source: string; className?: string }) {
  const html = useMemo(
    () =>
      DOMPurify.sanitize(marked.parse(source, { async: false }), {
        USE_PROFILES: { html: true },
        FORBID_TAGS: ["style", "iframe", "form", "input", "img"],
        ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|#)/i,
      }),
    [source],
  );
  // eslint-disable-next-line react/no-danger -- sanitized above
  return <div className={`prose-campus ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}
