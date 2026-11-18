// The Lyrx page: find a song, open the best match, show it in four columns; your saved songs.
import { useEffect, useState } from "react";
import {
  getSongVersions,
  listSavedSongs,
  removeSavedSong,
  searchSongs,
} from "./lyrics/api";
import { OtherMatches } from "./lyrics/OtherMatches";
import { SavedSongs } from "./lyrics/SavedSongs";
import { SearchForm } from "./lyrics/SearchForm";
import type { ApiResult, Line, SearchResult, Song } from "./lyrics/types";
import { VersionsTable } from "./lyrics/VersionsTable";
import { WaitingStatus } from "./lyrics/WaitingStatus";

export const FALLBACK_MESSAGE = "Something went wrong. Try again.";
export const SERVER_UNREACHABLE_MESSAGE =
  "Could not reach the Lyrx server. Is it running?";
const FINDING_TEXT = "Finding the song…";
const OPENING_TEXT = "Getting the lyrics and translating…";

type Status = "idle" | "finding" | "opening";

interface Shown {
  song: Song;
  lines: Line[];
  fromLibrary: boolean;
  // How long the steps took, in milliseconds; shown for development.
  findMs?: number;
  versionsMs: number;
}

// "Found in 0.4 s · versions in 12.3 s", or the library or versions part alone.
export function timingText(
  shown: Pick<Shown, "fromLibrary" | "findMs" | "versionsMs">,
): string {
  const versions = formatSeconds(shown.versionsMs);
  if (shown.fromLibrary) {
    return `Opened from your songs in ${versions}`;
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
  const [savedSongs, setSavedSongs] = useState<Song[]>([]);
  const busy = status !== "idle";

  async function refreshSavedSongs() {
    const result = await listSavedSongs();
    if (result.kind === "ok") {
      setSavedSongs(result.value);
    }
  }

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

  async function openSong(id: number, findMs?: number) {
    setStatus("opening");
    setShown(null);
    setError(null);
    const started = performance.now();
    const result = await getSongVersions(id);
    setStatus("idle");
    if (result.kind === "ok") {
      setShown({
        ...result.value,
        findMs,
        versionsMs: performance.now() - started,
      });
      void refreshSavedSongs();
    } else {
      setError(messageFor(result));
    }
  }

  async function find(query: string) {
    setStatus("finding");
    setResults([]);
    setShown(null);
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
    await openSong(best.id, findMs);
  }

  async function removeSong(song: Song) {
    setError(null);
    const result = await removeSavedSong(song.id);
    if (result.kind === "ok") {
      setSavedSongs((songs) => songs.filter((saved) => saved.id !== song.id));
      setResults((found) =>
        found.map((match) =>
          match.id === song.id ? { ...match, saved: false } : match,
        ),
      );
    } else {
      setError(messageFor(result));
    }
  }

  const otherResults = results.filter((result) => result.id !== shown?.song.id);

  return (
    <main>
      <h1>Lyrx</h1>
      <SearchForm
        busy={busy}
        onSearch={(query) => {
          void find(query);
        }}
      />
      <WaitingStatus
        text={
          status === "finding"
            ? FINDING_TEXT
            : status === "opening"
              ? OPENING_TEXT
              : null
        }
      />
      {error !== null && (
        <p role="alert" className="error">
          <strong>Error:</strong> {error}
        </p>
      )}
      {shown !== null && (
        <>
          <p className="song-line">
            <strong>{shown.song.track}</strong> — {shown.song.artist}{" "}
            <span className="muted">(lyrics from LRCLIB)</span>
          </p>
          <p className="muted timing">{timingText(shown)}</p>
        </>
      )}
      <OtherMatches
        results={otherResults}
        busy={busy}
        onPick={(result) => {
          void openSong(result.id);
        }}
      />
      {shown !== null && <VersionsTable lines={shown.lines} />}
      <SavedSongs
        songs={savedSongs}
        busy={busy}
        onOpen={(song) => {
          void openSong(song.id);
        }}
        onRemove={(song) => {
          void removeSong(song);
        }}
      />
    </main>
  );
}
