// The home page: your saved songs as tiles, sorted by recent, title, or artist; a welcome when empty.
import { useState } from "react";
import type { SavedSong } from "../lyrics/types";
import { SongTile } from "./SongTile";
import { sortSongs } from "./songTiles";
import type { SortOrder } from "./songTiles";

export const EMPTY_LIBRARY_TEXT = "Your songs will show up here.";
export const EMPTY_LIBRARY_HINT =
  "Type a song you love in the search box: title, artist, or both.";

const SORT_ORDERS: { order: SortOrder; label: string }[] = [
  { order: "recent", label: "Recent" },
  { order: "title", label: "A–Z" },
  { order: "artist", label: "Artist" },
];

interface LibraryPageProps {
  songs: SavedSong[];
  onOpen: (song: SavedSong) => void;
  onRemove: (song: SavedSong) => void;
}

export function LibraryPage({ songs, onOpen, onRemove }: LibraryPageProps) {
  const [order, setOrder] = useState<SortOrder>("recent");
  // "Now" for the "Opened …" labels, read once when the library opens.
  const [nowMs] = useState(() => Date.now());

  if (songs.length === 0) {
    return (
      <section className="page library-empty">
        <h1>{EMPTY_LIBRARY_TEXT}</h1>
        <p className="dim">{EMPTY_LIBRARY_HINT}</p>
      </section>
    );
  }

  return (
    <section className="page" aria-labelledby="library-heading">
      <div className="library-head">
        <div>
          <h1 id="library-heading">Your songs</h1>
          <p className="dim">
            {songs.length === 1 ? "1 saved" : `${String(songs.length)} saved`}.
            Pick one to keep learning.
          </p>
        </div>
        <div className="segmented" role="group" aria-label="Sort songs">
          {SORT_ORDERS.map(({ order: option, label }) => (
            <button
              key={option}
              type="button"
              aria-pressed={order === option}
              onClick={() => {
                setOrder(option);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <ul className="tile-grid">
        {sortSongs(songs, order).map((song) => (
          <SongTile
            key={song.id}
            song={song}
            nowMs={nowMs}
            onOpen={onOpen}
            onRemove={onRemove}
          />
        ))}
      </ul>
    </section>
  );
}
