// The player bar's controls: previous / play / next, loop, the position slider, sync, the video toggle.
import { formatClock, formatOffset } from "./playback";
import type { Progress } from "./types";

interface PlayerControlsProps {
  progress: Progress;
  offsetMs: number;
  hasTimings: boolean;
  hasVideo: boolean;
  videoShown: boolean;
  looping: boolean;
  // A line is sung and the song has timings, so there is a line to loop.
  canLoop: boolean;
  onToggleLoop: () => void;
  onNudge: (direction: 1 | -1) => void;
  onToggleVideo: () => void;
  onTogglePlay: () => void;
  onSeek: (milliseconds: number) => void;
  onPreviousLine: () => void;
  onNextLine: () => void;
}

// Previous / play / next, loop, the position slider, the sync nudge, and the video toggle.
export function PlayerControls(props: PlayerControlsProps) {
  const { progress, offsetMs, hasTimings } = props;
  const timeMs = progress.timeMs ?? 0;
  const durationMs = progress.durationMs ?? 0;

  return (
    <>
      <div className="transport">
        <button
          type="button"
          className="icon-button"
          aria-label="Previous line"
          disabled={!hasTimings}
          onClick={props.onPreviousLine}
        >
          <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
            <path d="M19 20 9 12l10-8v16z" />
            <path d="M5 19V5" />
          </svg>
        </button>
        <button
          type="button"
          className="play-button"
          aria-label={progress.playing ? "Pause" : "Play"}
          onClick={props.onTogglePlay}
        >
          <svg
            viewBox="0 0 24 24"
            className="icon icon-filled"
            aria-hidden="true"
          >
            <path
              d={
                progress.playing
                  ? "M7 5h4v14H7zM13 5h4v14h-4z"
                  : "M8 5v14l11-7z"
              }
            />
          </svg>
        </button>
        <button
          type="button"
          className="icon-button"
          aria-label="Next line"
          disabled={!hasTimings}
          onClick={props.onNextLine}
        >
          <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
            <path d="M5 4l10 8-10 8V4z" />
            <path d="M19 5v14" />
          </svg>
        </button>
        <button
          type="button"
          className="icon-button"
          aria-label="Loop line"
          aria-pressed={props.looping}
          disabled={!props.canLoop}
          onClick={props.onToggleLoop}
        >
          <LoopIcon />
        </button>
      </div>
      <div className="position">
        <span>{formatClock(timeMs)}</span>
        <label htmlFor="position" className="visually-hidden">
          Position
        </label>
        <input
          id="position"
          type="range"
          min={0}
          max={durationMs}
          step={100}
          value={Math.min(timeMs, durationMs)}
          disabled={durationMs === 0}
          onChange={(event) => {
            props.onSeek(Number(event.target.value));
          }}
        />
        <span>{formatClock(durationMs)}</span>
      </div>
      {hasTimings && (
        <div className="sync" role="group" aria-label="Sync">
          <button
            type="button"
            className="pill-button"
            onClick={() => {
              props.onNudge(-1);
            }}
          >
            Earlier
          </button>
          <span aria-live="polite">Sync: {formatOffset(offsetMs)}</span>
          <button
            type="button"
            className="pill-button"
            onClick={() => {
              props.onNudge(1);
            }}
          >
            Later
          </button>
        </div>
      )}
      {props.hasVideo && (
        <button
          type="button"
          className="icon-button"
          aria-label="Show video"
          aria-pressed={props.videoShown}
          onClick={props.onToggleVideo}
        >
          <VideoIcon />
        </button>
      )}
    </>
  );
}

export function LoopIcon() {
  return (
    <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
      <path d="M17 2l4 4-4 4" />
      <path d="M3 11V9a3 3 0 0 1 3-3h15" />
      <path d="M7 22l-4-4 4-4" />
      <path d="M21 13v2a3 3 0 0 1-3 3H3" />
    </svg>
  );
}

export function VideoIcon() {
  return (
    <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
      <rect x="2" y="5" width="15" height="14" rx="2" />
      <path d="m17 10 5-3v10l-5-3" />
    </svg>
  );
}
