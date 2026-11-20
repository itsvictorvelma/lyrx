// A song: its header row (or the Focus strip), the lyrics rows, the player bar fixed below, and the study tools.
import { useCallback, useEffect, useRef, useState } from "react";
import { goBack } from "../routing";
import { HideColumnToggles, PhoneTabs } from "./ColumnButtons";
import { OtherMatches } from "./OtherMatches";
import { useFollowLine } from "./followLine";
import { useHiddenColumns } from "./hiddenColumns";
import { loopRange } from "./lineLoop";
import { currentLineIndex, hasTimings, LEAD_IN_MS } from "./playback";
import type { AudioClock } from "./playback";
import { PlayerBar } from "./PlayerBar";
import { SaveButton } from "./SaveButton";
import { ShortcutList } from "./ShortcutList";
import { focusSearchBox } from "../header/SearchForm";
import { SHORTCUT_LIST, useShortcuts } from "./shortcuts";
import type { Shortcut } from "./shortcuts";
import type {
  Line,
  Playback,
  Progress,
  SearchResult,
  Song,
  VersionColumn,
} from "./types";
import { VersionsTable } from "./VersionsTable";

const SYNCED_TEXT = "Synced lyrics";
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
  const [phoneColumn, setPhoneColumn] = useState<VersionColumn>("hiragana");
  const { hidden, revealed, toggleColumn, revealCell } = useHiddenColumns();
  // The line being looped; null when not looping. Never saved.
  const [loopLine, setLoopLine] = useState<number | null>(null);
  const [shortcutListOpen, setShortcutListOpen] = useState(false);
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

  const playingLine =
    progress.timeMs === null
      ? null
      : currentLineIndex(lines, progress.timeMs + LEAD_IN_MS, offsetMs);
  // While looping, the looped line is the sung one, even in the lead-in to the line after it.
  const currentLine = loopLine ?? playingLine;
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

  // Moving to a line while looping moves the loop there too.
  function seekToLine(line: Line | undefined) {
    if (line?.startMs !== null && line?.startMs !== undefined) {
      clock.current?.seekMs(line.startMs + offsetMs);
      readProgress();
      if (loopLine !== null) {
        setLoopLine(line.index);
      }
    }
  }

  const timedLines = lines.filter((line) => line.startMs !== null);

  function previousLine() {
    const before = timedLines.filter(
      (line) => currentLine !== null && line.index < currentLine,
    );
    seekToLine(before.at(-1) ?? timedLines[0]);
  }

  function nextLine() {
    seekToLine(
      timedLines.find(
        (line) => currentLine === null || line.index > currentLine,
      ),
    );
  }

  function togglePlay() {
    if (clock.current?.isPlaying() === true) {
      clock.current.pause();
    } else {
      clock.current?.play();
    }
    readProgress();
  }

  // Always true while looping, so the loop can be turned off.
  const canLoop = timed && currentLine !== null;
  function toggleLoop() {
    setLoopLine(loopLine === null ? currentLine : null);
  }

  // Past the looped line's end, jump back to its start. Runs on each progress poll.
  const loop =
    loopLine === null
      ? null
      : loopRange(lines, loopLine, offsetMs, progress.durationMs);
  const loopStartMs = loop?.startMs ?? null;
  const loopEndMs = loop?.endMs ?? null;
  useEffect(() => {
    if (
      loopStartMs !== null &&
      loopEndMs !== null &&
      progress.timeMs !== null &&
      progress.timeMs >= loopEndMs
    ) {
      clock.current?.seekMs(loopStartMs);
    }
  }, [loopStartMs, loopEndMs, progress.timeMs]);

  // A shortcut does what its button does, and nothing when that button is disabled.
  function runShortcut(shortcut: Shortcut) {
    switch (shortcut.kind) {
      case "togglePlay":
        togglePlay();
        break;
      case "previousLine":
        if (timed) previousLine();
        break;
      case "nextLine":
        if (timed) nextLine();
        break;
      case "toggleLoop":
        if (canLoop) toggleLoop();
        break;
      case "toggleColumn":
        toggleColumn(shortcut.column);
        break;
      case "toggleFocus":
        props.onFocusChange(!focus);
        break;
      case "escape":
        if (shortcutListOpen) {
          setShortcutListOpen(false);
        } else if (focus) {
          props.onFocusChange(false);
        }
        break;
      case "toggleShortcutList":
        setShortcutListOpen((open) => !open);
        break;
      case "focusSearch":
        focusSearchBox();
        break;
    }
  }
  useShortcuts(runShortcut);

  return (
    <section className={focus ? "song-page is-focus" : "song-page"}>
      {focus ? (
        <div className="focus-strip">
          <span lang="ja" className="focus-title">
            {song.track}
          </span>
          <span className="dim">{song.artist}</span>
          <span className="spacer" />
          <HideColumnToggles hidden={hidden} onToggle={toggleColumn} />
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
            aria-label="Back"
            onClick={goBack}
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
          <HideColumnToggles hidden={hidden} onToggle={toggleColumn} />
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
            hidden={hidden}
            revealed={revealed}
            onReveal={revealCell}
            loopLine={loopLine}
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
        track={song.track}
        artist={song.artist}
        savedVideoId={props.playback.videoId}
        offsetMs={offsetMs}
        hasTimings={timed}
        progress={progress}
        onOffsetChange={setOffsetMs}
        onVideoChange={setVideoId}
        onClock={handleClock}
        onTogglePlay={togglePlay}
        onSeek={(milliseconds) => {
          // Dragging the slider ends a loop.
          setLoopLine(null);
          clock.current?.seekMs(milliseconds);
          readProgress();
        }}
        onPreviousLine={previousLine}
        onNextLine={nextLine}
        looping={loopLine !== null}
        canLoop={canLoop}
        onToggleLoop={toggleLoop}
        shortcutListOpen={shortcutListOpen}
        onToggleShortcutList={() => {
          setShortcutListOpen((open) => !open);
        }}
      />
      {shortcutListOpen && (
        <ShortcutList
          shortcuts={SHORTCUT_LIST}
          onClose={() => {
            setShortcutListOpen(false);
          }}
        />
      )}
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
