// The Lyrx app: the header, then home at `/`, your songs at `/library`, a song at `/song/{id}`,
// or signing in at `/account`.
import { useCallback, useEffect, useRef, useState } from "react";
import { getAccount } from "./account/accountApi";
import { AccountPage } from "./account/AccountPage";
import { AccountContext, UNKNOWN_ACCOUNT } from "./account/useAccount";
import type { Account } from "./account/types";
import { Header } from "./header/Header";
import { focusSearchBox } from "./header/SearchForm";
import { HomePage } from "./home/HomePage";
import { LibraryPage } from "./library/LibraryPage";
import { RemovedMessage } from "./library/RemovedMessage";
import {
  getSongVersions,
  listRecentSongs,
  listSavedSongs,
  saveSong,
  unsaveSong,
  searchSongs,
} from "./lyrics/api";
import { SearchProgress } from "./lyrics/SearchProgress";
import { ShortcutList } from "./lyrics/ShortcutList";
import { SITE_SHORTCUT_LIST, useShortcuts } from "./lyrics/shortcuts";
import type { Stage } from "./lyrics/SearchProgress";
import { SongPage } from "./lyrics/SongPage";
import type {
  ApiResult,
  Line,
  Playback,
  RecentSong,
  SavedSong,
  SearchResult,
  Song,
} from "./lyrics/types";
import { HOME_PATH, navigate, songPath, useRoute } from "./routing";
import type { Route } from "./routing";

export const FALLBACK_MESSAGE = "Something went wrong. Try again.";
const SITE_NAME = "Lyrx";
const SERVER_UNREACHABLE_MESSAGE =
  "Could not reach the Lyrx server. Is it running?";

type Status = "idle" | Stage;

interface Shown {
  song: Song;
  lines: Line[];
  fromLibrary: boolean;
  playback: Playback;
  saved: boolean;
  // When this open happened; it keys the song page, so every open starts it fresh.
  openedAt: number;
  // How long the steps took, in milliseconds; shown for development.
  findMs?: number;
  versionsMs: number;
}

// "Found in 0.4 s · versions in 12.3 s", or the already-translated or versions part alone.
export function timingText(
  shown: Pick<Shown, "fromLibrary" | "findMs" | "versionsMs">,
): string {
  const versions = formatSeconds(shown.versionsMs);
  if (shown.fromLibrary) {
    return `Already translated · opened in ${versions}`;
  }
  return shown.findMs === undefined
    ? `Versions in ${versions}`
    : `Found in ${formatSeconds(shown.findMs)} · versions in ${versions}`;
}

function formatSeconds(milliseconds: number): string {
  return `${(milliseconds / 1000).toFixed(1)} s`;
}

// Off the song page only these keys are shortcuts; the rest stay with the browser.
const SITE_SHORTCUTS = ["toggleShortcutList", "escape", "focusSearch"] as const;

// Home and the library: ? shows or hides the shortcut list, / jumps to the search box.
function SiteShortcuts() {
  const [open, setOpen] = useState(false);

  useShortcuts((shortcut) => {
    if (shortcut.kind === "toggleShortcutList") {
      setOpen((current) => !current);
    } else if (shortcut.kind === "escape") {
      setOpen(false);
    } else if (shortcut.kind === "focusSearch") {
      focusSearchBox();
    }
  }, SITE_SHORTCUTS);

  return open ? (
    <ShortcutList
      shortcuts={SITE_SHORTCUT_LIST}
      onClose={() => {
        setOpen(false);
      }}
    />
  ) : null;
}

// The browser tab's title for the page shown.
export function pageTitle(
  route: Route,
  song: Song | null,
  signedIn = false,
): string {
  if (route.page === "home") {
    return `${SITE_NAME} · Read Japanese songs line by line`;
  }
  if (route.page === "library") {
    return `Your songs · ${SITE_NAME}`;
  }
  if (route.page === "account") {
    return signedIn ? `Your account · ${SITE_NAME}` : `Sign in · ${SITE_NAME}`;
  }
  return song === null
    ? `Opening… · ${SITE_NAME}`
    : `${song.track} · ${song.artist} · ${SITE_NAME}`;
}

function messageFor(result: Exclude<ApiResult<unknown>, { kind: "ok" }>) {
  switch (result.kind) {
    case "error":
      return result.message;
    case "unreadable":
      return FALLBACK_MESSAGE;
    case "unreachable":
      return SERVER_UNREACHABLE_MESSAGE;
  }
}

export function App() {
  const [account, setAccount] = useState<Account>(UNKNOWN_ACCOUNT);
  // Read by the callbacks below without making them change on every sign-in.
  const signedIn = useRef(false);
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [shown, setShown] = useState<Shown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedSongs, setSavedSongs] = useState<SavedSong[]>([]);
  const [recentSongs, setRecentSongs] = useState<RecentSong[]>([]);
  // The song just removed, while its Undo message shows.
  const [removed, setRemoved] = useState<SavedSong | null>(null);
  const clearRemoved = useCallback(() => {
    setRemoved(null);
  }, []);
  const [focus, setFocus] = useState(false);
  // The song shown or being opened, so a route change opens a song only once.
  const openedId = useRef<number | null>(null);
  // How long the search took, handed to the open that follows it.
  const pendingFindMs = useRef<number | undefined>(undefined);
  const busy = status !== "idle";

  // A guest has no saved songs, so the server is not asked.
  const refreshSavedSongs = useCallback(async () => {
    if (!signedIn.current) {
      setSavedSongs([]);
      return;
    }
    const result = await listSavedSongs();
    if (result.kind === "ok") {
      setSavedSongs(result.value);
    }
  }, []);

  // A failed load keeps the row as it was; the home page hides it when empty.
  const refreshRecentSongs = useCallback(async () => {
    const result = await listRecentSongs();
    if (result.kind === "ok") {
      setRecentSongs(result.value);
    }
  }, []);

  // Every move clears the error and Focus mode. Home and the library refresh their songs, stop
  // a song still opening, and forget the open song, so opening it again fetches it fresh.
  const handleRouteChange = useCallback(
    (next: Route) => {
      setError(null);
      setFocus(false);
      if (next.page !== "song") {
        openedId.current = null;
        setStatus((current) => (current === "finding" ? current : "idle"));
        void refreshSavedSongs();
      }
      if (next.page === "home") {
        void refreshRecentSongs();
      }
    },
    [refreshSavedSongs, refreshRecentSongs],
  );
  const route = useRoute(handleRouteChange);

  const openSong = useCallback(
    async (id: number) => {
      openedId.current = id;
      const findMs = pendingFindMs.current;
      pendingFindMs.current = undefined;
      setStatus(findMs === undefined ? "opening" : "opening-found");
      setShown(null);
      setError(null);
      const started = performance.now();
      const result = await getSongVersions(id);
      if (openedId.current !== id) {
        return;
      }
      setStatus("idle");
      if (result.kind === "ok") {
        setShown({
          ...result.value,
          findMs,
          openedAt: started,
          versionsMs: performance.now() - started,
        });
        void refreshSavedSongs();
        return;
      }
      openedId.current = null;
      // A song the server does not have is an unknown address: show home instead.
      if (result.kind === "error" && result.code === "song_not_found") {
        navigate(HOME_PATH, { replace: true });
      }
      setError(messageFor(result));
    },
    [refreshSavedSongs],
  );

  // Who is signed in, their saved songs, and the recent songs load once when the page opens.
  // A failed check counts as a guest.
  useEffect(() => {
    let active = true;
    void getAccount().then((result) => {
      if (!active) {
        return;
      }
      const username = result.kind === "ok" ? result.value : null;
      signedIn.current = username !== null;
      setAccount({ username, checked: true });
      if (username !== null) {
        void refreshSavedSongs();
      }
    });
    void listRecentSongs().then((result) => {
      if (active && result.kind === "ok") {
        setRecentSongs(result.value);
      }
    });
    return () => {
      active = false;
    };
  }, [refreshSavedSongs]);

  // A song address opens that song, unless it is already shown or opening.
  useEffect(() => {
    if (route.page === "song" && openedId.current !== route.id) {
      void openSong(route.id);
    }
  }, [route, openSong]);

  async function find(query: string) {
    // A song still opening must not end this search when its reply arrives.
    openedId.current = null;
    setStatus("finding");
    setResults([]);
    setError(null);
    const started = performance.now();
    const result = await searchSongs(query);
    const findMs = performance.now() - started;
    if (result.kind !== "ok") {
      setStatus("idle");
      setError(messageFor(result));
      return;
    }
    setResults(result.value);
    const best = result.value[0];
    if (best === undefined) {
      setStatus("idle");
      return;
    }
    pendingFindMs.current = findMs;
    navigate(songPath(best.id));
  }

  // No confirm box: the Undo message puts the song back, with its video and sync.
  async function removeSong(song: SavedSong) {
    setError(null);
    const result = await unsaveSong(song.id);
    if (result.kind === "ok") {
      setSavedSongs((songs) => songs.filter((saved) => saved.id !== song.id));
      markSaved(song.id, false);
      setRemoved(song);
    } else {
      setError(messageFor(result));
    }
  }

  async function undoRemove(song: SavedSong) {
    setRemoved(null);
    const result = await saveSong(song.id, {
      videoId: song.videoId,
      offsetMs: song.offsetMs,
    });
    if (result.kind === "ok") {
      markSaved(song.id, true);
      void refreshSavedSongs();
    } else {
      setError(messageFor(result));
    }
  }

  // Back to the song that sent the guest to sign in, replacing /account so Back skips it.
  function handleSignedIn(username: string, returnTo: string | null) {
    signedIn.current = true;
    setAccount({ username, checked: true });
    navigate(returnTo ?? HOME_PATH, { replace: true });
  }

  function handleSignedOut() {
    signedIn.current = false;
    setAccount({ username: null, checked: true });
    setSavedSongs([]);
    setResults([]);
    setRemoved(null);
    navigate(HOME_PATH);
  }

  // Keeps the search results' "saved" marks in step with the library.
  function markSaved(id: number, saved: boolean) {
    setResults((found) =>
      found.map((match) => (match.id === id ? { ...match, saved } : match)),
    );
  }

  const songShown =
    route.page === "song" && shown?.song.id === route.id ? shown : null;

  useEffect(() => {
    document.title = pageTitle(
      route,
      songShown?.song ?? null,
      account.username !== null,
    );
  }, [route, songShown, account]);

  return (
    <AccountContext.Provider value={account}>
      <div className={songShown !== null && !busy ? "app is-song" : "app"}>
        {!focus && (
          <Header
            busy={busy}
            showSearch={route.page !== "home"}
            currentPage={route.page}
            onSearch={(query) => {
              void find(query);
            }}
          />
        )}
        {route.page !== "song" && <SiteShortcuts />}
        <main className="app-main">
          {error !== null && (
            <p role="alert" className="error page-error">
              <strong>Error:</strong> {error}
            </p>
          )}
          {busy ? (
            <SearchProgress stage={status} />
          ) : route.page === "home" ? (
            <HomePage
              savedSongs={savedSongs}
              recentSongs={recentSongs}
              onSearch={(query) => {
                void find(query);
              }}
              onOpenSong={(id) => {
                navigate(songPath(id));
              }}
            />
          ) : route.page === "account" ? (
            <AccountPage
              onSignedIn={(username) => {
                handleSignedIn(username, route.returnTo);
              }}
              onSignedOut={handleSignedOut}
            />
          ) : route.page === "library" ? (
            <LibraryPage
              songs={savedSongs}
              onOpen={(song) => {
                navigate(songPath(song.id));
              }}
              onRemove={(song) => {
                void removeSong(song);
              }}
            />
          ) : (
            songShown !== null && (
              <SongPage
                key={songShown.openedAt}
                song={songShown.song}
                lines={songShown.lines}
                playback={songShown.playback}
                saved={songShown.saved}
                timing={timingText(songShown)}
                otherMatches={results.filter(
                  (result) => result.id !== songShown.song.id,
                )}
                focus={focus}
                onPickMatch={(match) => {
                  navigate(songPath(match.id));
                }}
                onFocusChange={setFocus}
                onSavedChange={(saved) => {
                  markSaved(songShown.song.id, saved);
                }}
              />
            )
          )}
        </main>
        <RemovedMessage
          song={removed}
          onUndo={(song) => {
            void undoRemove(song);
          }}
          onDone={clearRemoved}
        />
      </div>
    </AccountContext.Provider>
  );
}
