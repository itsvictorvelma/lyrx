// Page addresses: `/` home, `/library` your songs, `/song/{id}` a song; Back and Forward work.
import { useEffect, useState } from "react";

// A whole number from 1 up, short enough to stay exact in JavaScript.
const SONG_PATH = /^\/song\/([1-9][0-9]{0,14})\/?$/;

const LIBRARY_PATH_PATTERN = /^\/library\/?$/;

export const HOME_PATH = "/";
export const LIBRARY_PATH = "/library";

export type Route =
  { page: "home" } | { page: "library" } | { page: "song"; id: number };

// The page for an address; anything unknown is home.
export function parseRoute(path: string): Route {
  if (LIBRARY_PATH_PATTERN.test(path)) {
    return { page: "library" };
  }
  const match = SONG_PATH.exec(path);
  const id = match?.[1] === undefined ? NaN : Number(match[1]);
  return Number.isSafeInteger(id) ? { page: "song", id } : { page: "home" };
}

export function songPath(id: number): string {
  return `/song/${String(id)}`;
}

// Moves to an address and tells `useRoute` listeners; `replace` swaps the current history entry.
export function navigate(path: string, { replace = false } = {}): void {
  if (replace) {
    window.history.replaceState(null, "", path);
  } else if (window.location.pathname !== path) {
    window.history.pushState(null, "", path);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

// The current page, updated on Back, Forward, and `navigate`; `onChange` hears each move.
export function useRoute(onChange: (route: Route) => void): Route {
  const [route, setRoute] = useState(() =>
    parseRoute(window.location.pathname),
  );

  useEffect(() => {
    function update() {
      const next = parseRoute(window.location.pathname);
      setRoute(next);
      onChange(next);
    }
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("popstate", update);
    };
  }, [onChange]);

  return route;
}
