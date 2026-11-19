// Calm following: the lyrics stay still until the sung line passes 60% of the view, then glide once.
import { useEffect } from "react";
import type { RefObject } from "react";

// Scroll only when the sung row passes this share of the view's height...
export const SCROLL_AT = 0.6;
// ...and then stop with the row this far from the top.
export const LAND_AT = 0.2;

// Positions in the view's own coordinates: how far each edge is from the view's top.
interface RowSpan {
  top: number;
  bottom: number;
}

// Where to scroll the view, or null to leave it still.
export function scrollTarget(
  row: RowSpan,
  viewScrollTop: number,
  viewHeight: number,
): number | null {
  const tooLow = row.bottom > viewScrollTop + viewHeight * SCROLL_AT;
  const above = row.top < viewScrollTop;
  if (!tooLow && !above) {
    return null;
  }
  return Math.max(0, row.top - viewHeight * LAND_AT);
}

function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

// Keeps the sung row in view while `following`; `rowSelector` finds it inside the view.
// `layout` changes when row heights do (Focus mode), so the row is checked again then.
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
    const rowBox = row.getBoundingClientRect();
    const top = rowBox.top - viewBox.top + view.scrollTop;
    const target = scrollTarget(
      { top, bottom: top + rowBox.height },
      view.scrollTop,
      view.clientHeight,
    );
    if (target !== null) {
      view.scrollTo({
        top: target,
        behavior: prefersReducedMotion() ? "auto" : "smooth",
      });
    }
  }, [viewRef, currentLine, following, rowSelector, layout]);
}
