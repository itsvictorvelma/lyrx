// A song: its header row (or the Focus strip), the lyrics rows, and the player bar fixed below.
import { useCallback, useEffect, useRef, useState } from "react";
import { navigate } from "../routing";
import { OtherMatches } from "./OtherMatches";
import { useFollowLine } from "./followLine";
import { currentLineIndex, hasTimings, LEAD_IN_MS } from "./playback";
import type { AudioClock } from "./playback";
import { PlayerBar } from "./PlayerBar";
import { SaveButton } from "./SaveButton";
import type { Line, Playback, Progress, SearchResult, Song } from "./types";
import { VersionsTable } from "./VersionsTable";
import type { PhoneColumn } from "./VersionsTable";

export const SYNCED_TEXT = "Synced lyrics";
export const NO_TIMINGS_TEXT = "No line timings for this song.";
const POLL_MS = 200;
export const BACK_TO_LINE_TEXT = "Back to the current line";
// Keys that scroll the lyrics when a line in them has focus; pressing one pauses following.
const SCROLL_KEYS = new Set([
  "ArrowUp",
  "ArrowDown",
  "PageUp",
  "PageDown",
  "Home",
  "End",
]);
const STOPPED: Progress = { timeMs: null, durationMs: null, playing: false };

const PHONE_COLUMNS: { column: PhoneColumn; label: string; lang: string }[] = [
  { column: "hiragana", label: "かな", lang: "ja" },
  { column: "romaji", label: "Romaji", lang: "en" },
  { column: "english", label: "EN", lang: "en" },
];

interface SongPageProps {
  song: Song;
  lines: Line[];
  playback: Playback;
  saved: boolean;
  timing: string;
  otherMatches: SearchResult[];
  focus: boolean;
  onPickMatch: (match: SearchResult) => void;
  onFocusChange: (focus: boolean) => void;
  onSavedChange: (saved: boolean) => void;
}

export function SongPage(props: SongPageProps) {
  const { song, lines, focus } = props;
  const [offsetMs, setOffsetMs] = useState(props.playback.offsetMs);
  const [videoId, setVideoId] = useState(props.playback.videoId);
  const [saved, setSaved] = useState(props.saved);
  const [progress, setProgress] = useState<Progress>(STOPPED);
  const [phoneColumn, setPhoneColumn] = useState<PhoneColumn>("hiragana");
  // The player now loaded, if any; read on a timer, so it is not state.
  const clock = useRef<AudioClock | null>(null);
  const lyricsRef = useRef<HTMLDivElement>(null);
  // Off once the learner scrolls the lyrics themselves, until they press "Back to the current line".
  const [following, setFollowing] = useState(true);
  const timed = hasTimings(lines);

  const readProgress = useCallback(() => {
    setProgress((previous) => {
      const next = readClock(clock.current);
      return sameProgress(previous, next) ? previous : next;
    });
  }, []);

  const handleClock = useCallback(
    (next: AudioClock | null) => {
      clock.current = next;
      readProgress();
    },
    [readProgress],
  );

  useEffect(() => {
    const timer = window.setInterval(readProgress, POLL_MS);
    return () => {
      window.clearInterval(timer);
    };
  }, [readProgress]);

  const currentLine =
    progress.timeMs === null
      ? null
      : currentLineIndex(lines, progress.timeMs + LEAD_IN_MS, offsetMs);
  useFollowLine(
    lyricsRef,
    currentLine,
    following,
    "tr.current",
    focus ? "focus" : "normal",
  );

  // Only the learner's own scrolling pauses following, never the page's.
  // ponytail: dragging the scrollbar doesn't pause; a pointer listener on the scrollbar could add it.
  function pauseFollowing() {
    if (currentLine !== null) {
      setFollowing(false);
    }
  }

  function seekToLine(line: Line | undefined) {
    if (line?.startMs !== null && line?.startMs !== undefined) {
      clock.current?.seekMs(line.startMs + offsetMs);
      readProgress();
    }
  }

  const timedLines = lines.filter((line) => line.startMs !== null);

  return (
    <section className={focus ? "song-page is-focus" : "song-page"}>
      {focus ? (
        <div className="focus-strip">
          <span lang="ja" className="focus-title">
            {song.track}
          </span>
          <span className="dim">{song.artist}</span>
          <span className="spacer" />
          <PhoneTabs value={phoneColumn} onChange={setPhoneColumn} />
          <button
            type="button"
            className="pill-button"
            onClick={() => {
              props.onFocusChange(false);
            }}
          >
            <FocusIcon exit /> Exit focus
          </button>
        </div>
      ) : (
        <div className="song-head">
          <button
            type="button"
            className="icon-button"
            aria-label="Back to your songs"
            onClick={() => {
              navigate("/");
            }}
          >
            <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
              <path d="M19 12H5" />
              <path d="m12 19-7-7 7-7" />
            </svg>
          </button>
          <div className="song-title-block">
            <h1 lang="ja">{song.track}</h1>
            <p className="dim song-meta">
              <span>{song.artist}</span>
              <span aria-hidden="true">·</span>
              {timed ? (
                <span className="synced">
                  <span className="live-dot" aria-hidden="true" />
                  {SYNCED_TEXT}
                </span>
              ) : (
                <span>{NO_TIMINGS_TEXT}</span>
              )}
              <span className="timing">{props.timing}</span>
            </p>
          </div>
          <PhoneTabs value={phoneColumn} onChange={setPhoneColumn} />
          <SaveButton
            songId={song.id}
            saved={saved}
            playback={{ videoId, offsetMs }}
            onSavedChange={(next) => {
              setSaved(next);
              props.onSavedChange(next);
            }}
          />
          <OtherMatches
            results={props.otherMatches}
            onPick={props.onPickMatch}
          />
          <button
            type="button"
            className="pill-button focus-button"
            onClick={() => {
              props.onFocusChange(true);
            }}
          >
            <FocusIcon /> Focus
          </button>
        </div>
      )}
      <div className="lyrics-area">
        <div
          ref={lyricsRef}
          className="lyrics-scroll"
          tabIndex={-1}
          onWheel={pauseFollowing}
          onTouchMove={pauseFollowing}
          onKeyDown={(event) => {
            if (SCROLL_KEYS.has(event.key)) {
              pauseFollowing();
            }
          }}
        >
          <VersionsTable
            lines={lines}
            currentLine={currentLine}
            phoneColumn={phoneColumn}
            onSeek={seekToLine}
          />
        </div>
        {!following && currentLine !== null && (
          <button
            type="button"
            className="pill-button back-to-line"
            onClick={() => {
              setFollowing(true);
              // The button goes away, so keep keyboard focus in the lyrics instead of the page.
              lyricsRef.current?.focus();
            }}
          >
            <span aria-hidden="true">↓</span> {BACK_TO_LINE_TEXT}
          </button>
        )}
      </div>
      <PlayerBar
        songId={song.id}
        savedVideoId={props.playback.videoId}
        offsetMs={offsetMs}
        hasTimings={timed}
        progress={progress}
        onOffsetChange={setOffsetMs}
        onVideoChange={setVideoId}
        onClock={handleClock}
        onTogglePlay={() => {
          if (clock.current?.isPlaying() === true) {
            clock.current.pause();
          } else {
            clock.current?.play();
          }
          readProgress();
        }}
        onSeek={(milliseconds) => {
          clock.current?.seekMs(milliseconds);
          readProgress();
        }}
        onPreviousLine={() => {
          const before = timedLines.filter(
            (line) => currentLine !== null && line.index < currentLine,
          );
          seekToLine(before.at(-1) ?? timedLines[0]);
        }}
        onNextLine={() => {
          seekToLine(
            timedLines.find(
              (line) => currentLine === null || line.index > currentLine,
            ),
          );
        }}
      />
    </section>
  );
}

function readClock(player: AudioClock | null): Progress {
  if (player === null) {
    return STOPPED;
  }
  return {
    timeMs: player.timeMs(),
    durationMs: player.durationMs(),
    playing: player.isPlaying(),
  };
}

function sameProgress(a: Progress, b: Progress): boolean {
  return (
    a.timeMs === b.timeMs &&
    a.durationMs === b.durationMs &&
    a.playing === b.playing
  );
}

interface PhoneTabsProps {
  value: PhoneColumn;
  onChange: (column: PhoneColumn) => void;
}

// On a phone, which version shows next to the original. Hidden on wider screens by styles.css.
function PhoneTabs({ value, onChange }: PhoneTabsProps) {
  return (
    <div
      className="segmented phone-tabs"
      role="group"
      aria-label="Second column"
    >
      {PHONE_COLUMNS.map(({ column, label, lang }) => (
        <button
          key={column}
          type="button"
          lang={lang}
          aria-pressed={value === column}
          onClick={() => {
            onChange(column);
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function FocusIcon({ exit = false }: { exit?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
      <path
        d={
          exit
            ? "M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"
            : "M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"
        }
      />
    </svg>
  );
}
