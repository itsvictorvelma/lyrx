// The Lyrx app: the header, then the library at `/` or a song at `/song/{id}`; search from anywhere.
import { useCallback, useEffect, useRef, useState } from "react";
import { Header } from "./header/Header";
import { LibraryPage } from "./library/LibraryPage";
import {
  getSongVersions,
  listSavedSongs,
  unsaveSong,
  searchSongs,
} from "./lyrics/api";
import { SearchProgress } from "./lyrics/SearchProgress";
import type { Stage } from "./lyrics/SearchProgress";
import { SongPage } from "./lyrics/SongPage";
import type {
  ApiResult,
  Line,
  Playback,
  SavedSong,
  SearchResult,
  Song,
} from "./lyrics/types";
import { navigate, songPath, useRoute } from "./routing";
import type { Route } from "./routing";

export const FALLBACK_MESSAGE = "Something went wrong. Try again.";
export const SERVER_UNREACHABLE_MESSAGE =
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
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [shown, setShown] = useState<Shown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedSongs, setSavedSongs] = useState<SavedSong[]>([]);
  const [focus, setFocus] = useState(false);
  // The song shown or being opened, so a route change opens a song only once.
  const openedId = useRef<number | null>(null);
  // How long the search took, handed to the open that follows it.
  const pendingFindMs = useRef<number | undefined>(undefined);
  const busy = status !== "idle";

  const refreshSavedSongs = useCallback(async () => {
    const result = await listSavedSongs();
    if (result.kind === "ok") {
      setSavedSongs(result.value);
    }
  }, []);

  // Every move clears the error and Focus mode. The library refreshes its tiles, stops a
  // song still opening, and forgets the open song, so opening it again fetches it fresh.
  const handleRouteChange = useCallback(
    (next: Route) => {
      setError(null);
      setFocus(false);
      if (next.page === "library") {
        openedId.current = null;
        setStatus((current) => (current === "finding" ? current : "idle"));
        void refreshSavedSongs();
      }
    },
    [refreshSavedSongs],
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
      // A song the server does not have is an unknown address: show the library instead.
      if (result.kind === "error" && result.code === "song_not_found") {
        navigate("/", { replace: true });
      }
      setError(messageFor(result));
    },
    [refreshSavedSongs],
  );

  // The saved songs load once when the page opens.
  useEffect(() => {
    let active = true;
    void listSavedSongs().then((result) => {
      if (active && result.kind === "ok") {
        setSavedSongs(result.value);
      }
    });
    return () => {
      active = false;
    };
  }, []);

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

  async function removeSong(song: SavedSong) {
    if (!window.confirm(`Remove ${song.track} from your songs?`)) {
      return;
    }
    setError(null);
    const result = await unsaveSong(song.id);
    if (result.kind === "ok") {
      setSavedSongs((songs) => songs.filter((saved) => saved.id !== song.id));
      markSaved(song.id, false);
    } else {
      setError(messageFor(result));
    }
  }

  // Keeps the search results' "saved" marks in step with the library.
  function markSaved(id: number, saved: boolean) {
    setResults((found) =>
      found.map((match) => (match.id === id ? { ...match, saved } : match)),
    );
  }

  const songShown =
    route.page === "song" && shown?.song.id === route.id ? shown : null;

  return (
    <div className={songShown !== null && !busy ? "app is-song" : "app"}>
      {!focus && (
        <Header
          busy={busy}
          onSearch={(query) => {
            void find(query);
          }}
        />
      )}
      <main className="app-main">
        {error !== null && (
          <p role="alert" className="error page-error">
            <strong>Error:</strong> {error}
          </p>
        )}
        {busy ? (
          <SearchProgress stage={status} />
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
    </div>
  );
}
