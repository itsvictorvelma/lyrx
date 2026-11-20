// Page addresses: `/` home, `/library` your songs, `/song/{id}` a song, `/account` signing in;
// Back and Forward work.
import { useEffect, useState } from "react";
import type { MouseEvent } from "react";

// A whole number from 1 up, short enough to stay exact in JavaScript.
const SONG_PATH = /^\/song\/([1-9][0-9]{0,14})\/?$/;

const LIBRARY_PATH_PATTERN = /^\/library\/?$/;
const ACCOUNT_PATH_PATTERN = /^\/account\/?$/;
// The query parameter on `/account` naming the song to go back to after signing in.
const RETURN_PARAMETER = "next";

export const HOME_PATH = "/";
export const LIBRARY_PATH = "/library";
export const ACCOUNT_PATH = "/account";

export type Route =
  | { page: "home" }
  | { page: "library" }
  | { page: "song"; id: number }
  // `returnTo` is a song address to go back to after signing in, or null.
  | { page: "account"; returnTo: string | null };

// The page for an address and its query; anything unknown is home.
export function parseRoute(path: string, query = ""): Route {
  if (LIBRARY_PATH_PATTERN.test(path)) {
    return { page: "library" };
  }
  if (ACCOUNT_PATH_PATTERN.test(path)) {
    const returnTo = new URLSearchParams(query).get(RETURN_PARAMETER);
    // Only a song address is followed, so a link cannot send someone off the site.
    const isSong = returnTo !== null && parseRoute(returnTo).page === "song";
    return { page: "account", returnTo: isSong ? returnTo : null };
  }
  const match = SONG_PATH.exec(path);
  const id = match?.[1] === undefined ? NaN : Number(match[1]);
  return Number.isSafeInteger(id) ? { page: "song", id } : { page: "home" };
}

export function songPath(id: number): string {
  return `/song/${String(id)}`;
}

// The sign-in page; with `returnTo`, signing in goes back to that song.
export function accountPath(returnTo?: string): string {
  if (returnTo === undefined) {
    return ACCOUNT_PATH;
  }
  return `${ACCOUNT_PATH}?${new URLSearchParams({ [RETURN_PARAMETER]: returnTo }).toString()}`;
}

function currentRoute(): Route {
  return parseRoute(window.location.pathname, window.location.search);
}

// Entries Lyrx adds are marked, so Back on a song knows there is a Lyrx page behind it.
const IN_APP_ENTRY = { lyrx: true };

// Moves to an address and tells `useRoute` listeners; `replace` swaps the current history entry.
export function navigate(path: string, { replace = false } = {}): void {
  if (replace) {
    window.history.replaceState(window.history.state, "", path);
  } else if (window.location.pathname + window.location.search !== path) {
    window.history.pushState(IN_APP_ENTRY, "", path);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

// The click handler for a same-site link: it moves without reloading the page.
export function followLink(path: string) {
  return (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigate(path);
  };
}

// Back to the Lyrx page before this one; home when this page was opened from outside.
export function goBack(): void {
  const state: unknown = window.history.state;
  const cameFromLyrx =
    typeof state === "object" && state !== null && "lyrx" in state;
  if (cameFromLyrx) {
    window.history.back();
  } else {
    navigate(HOME_PATH);
  }
}

// The current page, updated on Back, Forward, and `navigate`; `onChange` hears each move.
export function useRoute(onChange: (route: Route) => void): Route {
  const [route, setRoute] = useState(currentRoute);

  useEffect(() => {
    function update() {
      const next = currentRoute();
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
