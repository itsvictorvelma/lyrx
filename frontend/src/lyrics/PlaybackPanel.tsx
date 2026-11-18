// "Play along": a YouTube link or a file from this computer, and the Earlier/Later sync nudge.
import { useCallback, useState } from "react";
import { AudioFilePlayer } from "./AudioFilePlayer";
import { savePlayback } from "./api";
import { formatOffset, nudgeOffset, parseVideoId } from "./playback";
import type { AudioClock } from "./playback";
import { YouTubePlayer } from "./YouTubePlayer";

export const BAD_LINK_MESSAGE = "That doesn't look like a YouTube link.";
export const NO_TIMINGS_TEXT = "No line timings for this song.";
export const PLAYER_FAILED_MESSAGE =
  "Couldn't load the YouTube player. Try again.";
export const SAVE_FAILED_MESSAGE =
  "Couldn't save the video and sync for this song.";

type Source =
  { kind: "youtube"; videoId: string } | { kind: "file"; file: File } | null;

interface PlaybackPanelProps {
  songId: number;
  savedVideoId: string | null;
  offsetMs: number;
  hasTimings: boolean;
  onOffsetChange: (offsetMs: number) => void;
  onClock: (clock: AudioClock | null) => void;
}

export function PlaybackPanel({
  songId,
  savedVideoId,
  offsetMs,
  hasTimings,
  onOffsetChange,
  onClock,
}: PlaybackPanelProps) {
  const [link, setLink] = useState(
    savedVideoId === null ? "" : `https://youtu.be/${savedVideoId}`,
  );
  const [videoId, setVideoId] = useState(savedVideoId);
  const [source, setSource] = useState<Source>(
    savedVideoId === null ? null : { kind: "youtube", videoId: savedVideoId },
  );
  const [error, setError] = useState<string | null>(null);
  const showPlayerFailed = useCallback(() => {
    setError(PLAYER_FAILED_MESSAGE);
  }, []);

  // A 404 means the song is not saved, so nothing is kept; any other failure is said.
  async function save(playback: { videoId: string | null; offsetMs: number }) {
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
    setSource({ kind: "youtube", videoId: id });
    void save({ videoId: id, offsetMs });
  }

  function playFile(file: File | undefined) {
    if (file !== undefined) {
      setError(null);
      setSource({ kind: "file", file });
    }
  }

  function nudge(direction: 1 | -1) {
    const next = nudgeOffset(offsetMs, direction);
    onOffsetChange(next);
    void save({ videoId, offsetMs: next });
  }

  return (
    <section className="playback" aria-labelledby="playback-heading">
      <h2 id="playback-heading">Play along</h2>
      <form
        className="search-form"
        onSubmit={(event) => {
          event.preventDefault();
          playVideo();
        }}
      >
        <label htmlFor="youtube-link">YouTube link</label>
        <div className="search-row">
          <input
            id="youtube-link"
            type="url"
            value={link}
            onChange={(event) => {
              setLink(event.target.value);
            }}
          />
          <button type="submit">Play video</button>
        </div>
      </form>
      <p>
        <label>
          Play a file{" "}
          <input
            type="file"
            accept="audio/*"
            onChange={(event) => {
              playFile(event.target.files?.[0]);
            }}
          />
        </label>
      </p>
      {error !== null && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!hasTimings && <p className="muted">{NO_TIMINGS_TEXT}</p>}
      {source?.kind === "youtube" && (
        <YouTubePlayer
          videoId={source.videoId}
          onClock={onClock}
          onLoadError={showPlayerFailed}
        />
      )}
      {source?.kind === "file" && (
        <AudioFilePlayer file={source.file} onClock={onClock} />
      )}
      {hasTimings && (
        <div className="sync" role="group" aria-label="Sync">
          <button
            type="button"
            onClick={() => {
              nudge(-1);
            }}
          >
            Earlier
          </button>
          <span aria-live="polite">Sync: {formatOffset(offsetMs)}</span>
          <button
            type="button"
            onClick={() => {
              nudge(1);
            }}
          >
            Later
          </button>
        </div>
      )}
    </section>
  );
}
