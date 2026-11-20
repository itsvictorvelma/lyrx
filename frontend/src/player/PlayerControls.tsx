// The player bar's controls: previous / play / next, loop, position, volume, speed, sync, video.
import { formatClock, formatOffset, VOLUME_STEP } from "./playback";
import type { Progress } from "../types";
import {
  LoopIcon,
  NextIcon,
  PauseIcon,
  PlayIcon,
  PreviousIcon,
  VideoIcon,
  VolumeIcon,
} from "../icons";

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
  speed: number;
  onChangeSpeed: () => void;
  volume: number;
  onVolumeChange: (volume: number) => void;
  onToggleMute: () => void;
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
          <PreviousIcon />
        </button>
        <button
          type="button"
          className="play-button"
          aria-label={progress.playing ? "Pause" : "Play"}
          onClick={props.onTogglePlay}
        >
          {progress.playing ? <PauseIcon /> : <PlayIcon />}
        </button>
        <button
          type="button"
          className="icon-button"
          aria-label="Next line"
          disabled={!hasTimings}
          onClick={props.onNextLine}
        >
          <NextIcon />
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
      <div className="volume">
        <button
          type="button"
          className="icon-button"
          aria-label={props.volume > 0 ? "Mute" : "Unmute"}
          onClick={props.onToggleMute}
        >
          <VolumeIcon muted={props.volume === 0} />
        </button>
        <label htmlFor="volume" className="visually-hidden">
          Volume
        </label>
        <input
          id="volume"
          type="range"
          min={0}
          max={100}
          step={VOLUME_STEP}
          value={props.volume}
          aria-valuetext={`${String(props.volume)}%`}
          onChange={(event) => {
            props.onVolumeChange(Number(event.target.value));
          }}
        />
      </div>
      <button
        type="button"
        className="pill-button speed-button"
        aria-label={`Playback speed: ${String(props.speed)}×`}
        onClick={props.onChangeSpeed}
      >
        {props.speed}×
      </button>
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
          className="icon-button video-toggle"
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
