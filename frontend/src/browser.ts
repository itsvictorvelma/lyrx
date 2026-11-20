// What the page reads from the browser: media queries, and settings remembered on this browser.

// Whether a CSS media query matches now; false where `matchMedia` is missing (jsdom in tests).
export function matchesMedia(query: string): boolean {
  return (
    typeof window.matchMedia === "function" && window.matchMedia(query).matches
  );
}

export function prefersReducedMotion(): boolean {
  return matchesMedia("(prefers-reduced-motion: reduce)");
}

// A remembered setting, or null when none is stored or storage is blocked.
export function readSetting(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function storeSetting(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage blocked (private window): the choice lasts until the page closes.
  }
}
