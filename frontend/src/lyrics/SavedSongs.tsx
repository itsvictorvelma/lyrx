// "Your songs": the saved songs, most recently opened first, each with Open and Remove.
import { formatDuration } from "./OtherMatches";
import type { Song } from "./types";

interface SavedSongsProps {
  songs: Song[];
  busy: boolean;
  onOpen: (song: Song) => void;
  onRemove: (song: Song) => void;
}

export function SavedSongs({ songs, busy, onOpen, onRemove }: SavedSongsProps) {
  if (songs.length === 0) {
    return null;
  }
  return (
    <section className="saved-songs" aria-labelledby="saved-songs-heading">
      <h2 id="saved-songs-heading">Your songs</h2>
      <ul>
        {songs.map((song) => (
          <li key={song.id}>
            <button
              type="button"
              className="link-button"
              disabled={busy}
              onClick={() => {
                onOpen(song);
              }}
            >
              {song.track} — {song.artist},{" "}
              {formatDuration(song.durationSeconds)}
            </button>{" "}
            <button
              type="button"
              disabled={busy}
              aria-label={`Remove ${song.track}`}
              onClick={() => {
                onRemove(song);
              }}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
