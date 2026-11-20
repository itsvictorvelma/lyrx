// Steady following: the sung line stays about 35% down the lyrics, and each new line glides there.
import { useEffect } from "react";
import type { RefObject } from "react";
import { prefersReducedMotion } from "../browser";

// Where the sung row sits, as a share of the view's height from the top.
export const STEADY_AT = 0.35;
// How long one glide takes.
export const GLIDE_MS = 450;

// The scroll position that puts a row starting at `rowTop` 35% down the view, within what scrolls.
export function scrollTarget(
  rowTop: number,
  viewHeight: number,
  maxScroll: number,
): number {
  const target = rowTop - viewHeight * STEADY_AT;
  return Math.round(Math.min(Math.max(target, 0), Math.max(maxScroll, 0)));
}

// Where a glide from `from` to `to` is after `elapsedMs`: fast at first, then settling (ease-out).
export function glidePosition(
  from: number,
  to: number,
  elapsedMs: number,
): number {
  const progress = Math.min(Math.max(elapsedMs / GLIDE_MS, 0), 1);
  const eased = 1 - (1 - progress) ** 3;
  return from + (to - from) * eased;
}

// Keeps the sung row 35% down the view while `following`; `rowSelector` finds it inside the view.
// `layout` changes when row heights do (Focus mode, the phone tabs), so the row is placed again then.
// A new glide replaces one still running, so quick lines never stack up.
export function useFollowLine(
  viewRef: RefObject<HTMLElement | null>,
  currentLine: number | null,
  following: boolean,
  rowSelector: string,
  layout: string,
): void {
  useEffect(() => {
    const view = viewRef.current;
    const row = view?.querySelector<HTMLElement>(rowSelector) ?? null;
    // jsdom (the test browser) lays nothing out and has no scrollTo.
    if (!following || view === null || row === null || !("scrollTo" in view)) {
      return;
    }
    const viewBox = view.getBoundingClientRect();
    const rowTop =
      row.getBoundingClientRect().top - viewBox.top + view.scrollTop;
    const target = scrollTarget(
      rowTop,
      view.clientHeight,
      view.scrollHeight - view.clientHeight,
    );
    if (prefersReducedMotion()) {
      view.scrollTo({ top: target, behavior: "instant" });
      return;
    }
    const from = view.scrollTop;
    // Timed from the first frame's own clock, which is not always `performance.now()`'s.
    let started: number | null = null;
    let frame: number | null = null;
    function step(now: number) {
      started ??= now;
      const top = glidePosition(from, target, now - started);
      view?.scrollTo({ top, behavior: "instant" });
      frame = top === target ? null : requestAnimationFrame(step);
    }
    frame = requestAnimationFrame(step);
    return () => {
      if (frame !== null) {
        cancelAnimationFrame(frame);
      }
    };
  }, [viewRef, currentLine, following, rowSelector, layout]);
}
