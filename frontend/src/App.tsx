// The Lyrx page: find a song, open the best match, show it in four columns; paste as a fallback.
import { useState } from "react";
import { getPasteVersions, getSongVersions, searchSongs } from "./lyrics/api";
import { OtherMatches } from "./lyrics/OtherMatches";
import { PasteForm } from "./lyrics/PasteForm";
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
  song?: Song;
  lines: Line[];
  // How long the steps took, in milliseconds; shown for development.
  findMs?: number;
  versionsMs: number;
}

// "Found in 0.4 s · versions in 12.3 s", or just the versions part.
export function timingText(shown: Shown): string {
  const versions = formatSeconds(shown.versionsMs);
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
  const [pasteOpen, setPasteOpen] = useState(false);
  const busy = status !== "idle";

  async function openSong(id: number, findMs?: number) {
    setStatus("opening");
    setShown(null);
    setError(null);
    const started = performance.now();
    const result = await getSongVersions(id);
    setStatus("idle");
    if (result.kind === "ok") {
      setShown({
        song: result.value.song,
        lines: result.value.lines,
        findMs,
        versionsMs: performance.now() - started,
      });
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

  async function paste(lyrics: string) {
    setStatus("opening");
    setShown(null);
    setError(null);
    const started = performance.now();
    const result = await getPasteVersions(lyrics);
    setStatus("idle");
    if (result.kind === "ok") {
      setShown({
        lines: result.value,
        versionsMs: performance.now() - started,
      });
    } else {
      setError(messageFor(result));
    }
  }

  const otherResults = results.filter(
    (result) => result.id !== shown?.song?.id,
  );

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
      {shown?.song !== undefined && (
        <p className="song-line">
          <strong>{shown.song.track}</strong> — {shown.song.artist}{" "}
          <span className="muted">(lyrics from LRCLIB)</span>
        </p>
      )}
      {shown !== null && <p className="muted timing">{timingText(shown)}</p>}
      <OtherMatches
        results={otherResults}
        busy={busy}
        onPick={(result) => {
          void openSong(result.id);
        }}
      />
      {shown !== null && <VersionsTable lines={shown.lines} />}
      {pasteOpen ? (
        <PasteForm
          busy={busy}
          onSubmit={(lyrics) => {
            void paste(lyrics);
          }}
        />
      ) : (
        <button
          type="button"
          className="link-button"
          onClick={() => {
            setPasteOpen(true);
          }}
        >
          Paste the lyrics instead
        </button>
      )}
    </main>
  );
}
