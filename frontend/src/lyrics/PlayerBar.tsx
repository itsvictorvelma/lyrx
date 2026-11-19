// The player bar at the bottom of a song: audio controls, sync, the video window, and choosing audio.
import { useCallback, useState } from "react";
import { matchesMedia } from "../mediaQuery";
import { AudioFilePlayer } from "./AudioFilePlayer";
import { savePlayback } from "./api";
import { nudgeOffset, parseVideoId } from "./playback";
import type { AudioClock } from "./playback";
import { PlayerControls, VideoIcon } from "./PlayerControls";
import type { Playback, Progress } from "./types";
import { YouTubePlayer } from "./YouTubePlayer";

export const BAD_LINK_MESSAGE = "That doesn't look like a YouTube link.";
const PLAYER_FAILED_MESSAGE = "Couldn't load the YouTube player. Try again.";
const SAVE_FAILED_MESSAGE = "Couldn't save the video and sync for this song.";

// The width below which styles.css uses the phone layout.
const PHONE_QUERY = "(max-width: 719px)";

// The video window starts open, except on a phone, where it would leave little room for lyrics.
function startsWithVideoShown(): boolean {
  return !matchesMedia(PHONE_QUERY);
}

type Source =
  { kind: "youtube"; videoId: string } | { kind: "file"; file: File } | null;

interface PlayerBarProps {
  songId: number;
  savedVideoId: string | null;
  offsetMs: number;
  hasTimings: boolean;
  progress: Progress;
  onOffsetChange: (offsetMs: number) => void;
  onVideoChange: (videoId: string) => void;
  onClock: (clock: AudioClock | null) => void;
  onTogglePlay: () => void;
  onSeek: (milliseconds: number) => void;
  onPreviousLine: () => void;
  onNextLine: () => void;
}

export function PlayerBar(props: PlayerBarProps) {
  const { songId, savedVideoId, offsetMs, onOffsetChange } = props;
  const [link, setLink] = useState(
    savedVideoId === null ? "" : `https://youtu.be/${savedVideoId}`,
  );
  const [videoId, setVideoId] = useState(savedVideoId);
  const [source, setSource] = useState<Source>(
    savedVideoId === null ? null : { kind: "youtube", videoId: savedVideoId },
  );
  const [choosing, setChoosing] = useState(false);
  const [linkFormOpen, setLinkFormOpen] = useState(false);
  const [videoShown, setVideoShown] = useState(startsWithVideoShown);
  const [error, setError] = useState<string | null>(null);
  const showPlayerFailed = useCallback(() => {
    setError(PLAYER_FAILED_MESSAGE);
  }, []);

  // A 404 means the song is not in the library, so nothing is kept; any other failure is said.
  async function save(playback: Playback) {
    const result = await savePlayback(songId, playback);
    const notSaved =
      result.kind === "error" && result.code === "song_not_found";
    if (result.kind !== "ok" && !notSaved) {
      setError(SAVE_FAILED_MESSAGE);
    }
  }

  function playVideo() {
    const id = parseVideoId(link);
    if (id === null) {
      setError(BAD_LINK_MESSAGE);
      return;
    }
    setError(null);
    setVideoId(id);
    props.onVideoChange(id);
    setSource({ kind: "youtube", videoId: id });
    setVideoShown(startsWithVideoShown());
    setLinkFormOpen(false);
    setChoosing(false);
    void save({ videoId: id, offsetMs });
  }

  function playFile(file: File | undefined) {
    if (file !== undefined) {
      setError(null);
      setSource({ kind: "file", file });
      setLinkFormOpen(false);
      setChoosing(false);
    }
  }

  function nudge(direction: 1 | -1) {
    const next = nudgeOffset(offsetMs, direction);
    onOffsetChange(next);
    void save({ videoId, offsetMs: next });
  }

  const showChooser = source === null || choosing;

  return (
    <footer className="player-bar">
      {source?.kind === "youtube" && (
        <div className={videoShown ? "video-window" : "video-window is-hidden"}>
          <YouTubePlayer
            videoId={source.videoId}
            onClock={props.onClock}
            onLoadError={showPlayerFailed}
          />
          <button
            type="button"
            className="icon-button video-close"
            aria-label="Hide video"
            onClick={() => {
              setVideoShown(false);
            }}
          >
            <CloseIcon />
          </button>
        </div>
      )}
      {source?.kind === "file" && (
        <AudioFilePlayer file={source.file} onClock={props.onClock} />
      )}
      {linkFormOpen && (
        <form
          className="link-form"
          onSubmit={(event) => {
            event.preventDefault();
            playVideo();
          }}
        >
          <label htmlFor="youtube-link">YouTube link</label>
          <input
            id="youtube-link"
            type="url"
            placeholder="https://youtu.be/…"
            value={link}
            onChange={(event) => {
              setLink(event.target.value);
            }}
          />
          <button type="submit" className="pill-button">
            Play video
          </button>
        </form>
      )}
      {error !== null && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="player-row">
        {showChooser ? (
          <AudioChooser
            linkFormOpen={linkFormOpen}
            onToggleLink={() => {
              setLinkFormOpen((open) => !open);
            }}
            onFile={playFile}
          />
        ) : (
          <PlayerControls
            progress={props.progress}
            offsetMs={offsetMs}
            hasTimings={props.hasTimings}
            onTogglePlay={props.onTogglePlay}
            onSeek={props.onSeek}
            onPreviousLine={props.onPreviousLine}
            onNextLine={props.onNextLine}
            hasVideo={source.kind === "youtube"}
            videoShown={videoShown}
            onNudge={nudge}
            onToggleVideo={() => {
              setVideoShown((shown) => !shown);
            }}
          />
        )}
        {source !== null && (
          <button
            type="button"
            className="pill-button change-audio"
            aria-expanded={choosing}
            onClick={() => {
              setChoosing((open) => !open);
              setLinkFormOpen(false);
            }}
          >
            {choosing ? "Back to player" : "Change audio"}
          </button>
        )}
      </div>
    </footer>
  );
}

interface AudioChooserProps {
  linkFormOpen: boolean;
  onToggleLink: () => void;
  onFile: (file: File | undefined) => void;
}

// With no audio yet: add a YouTube link, or pick a file from this computer.
function AudioChooser({
  linkFormOpen,
  onToggleLink,
  onFile,
}: AudioChooserProps) {
  return (
    <div className="audio-chooser">
      <button
        type="button"
        className="pill-button"
        aria-expanded={linkFormOpen}
        onClick={onToggleLink}
      >
        <VideoIcon /> Add YouTube link
      </button>
      <label className="pill-button">
        Play a file
        <input
          type="file"
          accept="audio/*"
          className="visually-hidden"
          onChange={(event) => {
            onFile(event.target.files?.[0]);
          }}
        />
      </label>
    </div>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}
