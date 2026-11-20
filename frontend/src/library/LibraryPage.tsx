// Your songs (/library): saved songs as tiles, sorted and filtered; a welcome when empty, and a
// sign-in prompt for a guest.
import { useState } from "react";
import { isGuest, useAccount } from "../account/account";
import type { SavedSong } from "../types";
import { ACCOUNT_PATH, navigate } from "../routing";
import { SongTile } from "./SongTile";
import { filterSongs, sortSongs } from "./songTiles";
import type { SortOrder } from "./songTiles";

export const EMPTY_LIBRARY_TEXT = "Your songs will show up here.";
export const EMPTY_LIBRARY_HINT =
  "Type a song you love in the search box: title, artist, or both.";
export const GUEST_LIBRARY_TEXT = "Sign in to keep your songs here.";

// The filter box shows once there are more songs than fit in a glance.
export const FILTER_SHOWN_ABOVE = 8;

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

export function LibraryPage(props: LibraryPageProps) {
  const account = useAccount();
  if (isGuest(account)) {
    return (
      <section className="page library-empty">
        <h1>{GUEST_LIBRARY_TEXT}</h1>
        <p className="dim">Songs you save keep their video and sync.</p>
        <button
          type="button"
          className="find-button library-sign-in"
          onClick={() => {
            navigate(ACCOUNT_PATH);
          }}
        >
          Sign in
        </button>
      </section>
    );
  }
  return <SavedSongs {...props} />;
}

function SavedSongs({ songs, onOpen, onRemove }: LibraryPageProps) {
  const [order, setOrder] = useState<SortOrder>("recent");
  const [filter, setFilter] = useState("");
  // "Now" for the "Opened …" labels, read once when the library opens.
  const [nowMs] = useState(() => Date.now());

  // The filter applies only while its box shows, so hidden text never hides songs.
  const filterShown = songs.length > FILTER_SHOWN_ABOVE;
  const shown = sortSongs(
    filterShown ? filterSongs(songs, filter) : songs,
    order,
  );

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
      {filterShown && (
        <div className="library-filter">
          <label htmlFor="library-filter" className="visually-hidden">
            Filter your songs
          </label>
          <input
            id="library-filter"
            type="search"
            autoComplete="off"
            placeholder="Filter your songs"
            value={filter}
            onChange={(event) => {
              setFilter(event.target.value);
            }}
          />
        </div>
      )}
      {shown.length === 0 && (
        <p className="dim">No songs match "{filter.trim()}".</p>
      )}
      <ul className="tile-grid">
        {shown.map((song) => (
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
