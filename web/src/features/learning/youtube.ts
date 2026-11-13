// Completion when the video ends, without loading YouTube's script (no CSP change): the embed is opened
// with `enablejsapi=1`, we ask it to report its state over postMessage and listen for "ended" (0).
// Only messages from the YouTube origin AND from our own iframe count.

import { useEffect, useRef, type RefObject } from "react";

export const YOUTUBE_ORIGIN = "https://www.youtube-nocookie.com";
const ENDED = 0;

/** Embed URL with the JS API enabled for this page's origin. Merges into any query the API already set
 * (a lesson segment's ?start=&end=, UPS-045) instead of appending a second "?". */
export function playerSrc(embedUrl: string): string {
  const url = new URL(embedUrl);
  const params = { enablejsapi: "1", rel: "0", modestbranding: "1", origin: window.location.origin };
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  return url.toString();
}

function playerState(data: unknown): number | null {
  let message: unknown = data;
  if (typeof data === "string") {
    try {
      message = JSON.parse(data);
    } catch {
      return null;
    }
  }
  if (!message || typeof message !== "object") return null;
  const { event, info } = message as { event?: unknown; info?: unknown };
  if (event === "onStateChange" && typeof info === "number") return info;
  if (event === "infoDelivery" && info && typeof info === "object") {
    const state = (info as { playerState?: unknown }).playerState;
    return typeof state === "number" ? state : null;
  }
  return null;
}

/** Calls `onEnded` once when the video in `frame` finishes. */
export function useVideoEnded(frame: RefObject<HTMLIFrameElement | null>, onEnded: () => void, enabled = true): void {
  // The latest callback, read when the video ends: a new `onEnded` each render must not re-subscribe (and
  // postMessage to an iframe that has not loaded yet).
  const latest = useRef(onEnded);
  useEffect(() => {
    latest.current = onEnded;
  }, [onEnded]);

  useEffect(() => {
    if (!enabled) return;
    let fired = false;

    const subscribe = () => {
      const target = frame.current?.contentWindow;
      if (!target) return;
      target.postMessage(JSON.stringify({ event: "listening", id: 1, channel: "widget" }), YOUTUBE_ORIGIN);
      target.postMessage(JSON.stringify({ event: "command", func: "addEventListener", args: ["onStateChange"] }), YOUTUBE_ORIGIN);
    };

    const onMessage = (event: MessageEvent) => {
      if (event.origin !== YOUTUBE_ORIGIN || !frame.current || event.source !== frame.current.contentWindow) return;
      if (!fired && playerState(event.data) === ENDED) {
        fired = true;
        latest.current();
      }
    };

    window.addEventListener("message", onMessage);
    const node = frame.current;
    node?.addEventListener("load", subscribe);
    subscribe();
    return () => {
      window.removeEventListener("message", onMessage);
      node?.removeEventListener("load", subscribe);
    };
  }, [frame, enabled]);
}
