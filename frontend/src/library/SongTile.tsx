// One library tile: the art (thumbnail or first character), title, artist, last opened, Remove.
import type { SavedSong } from "../types";
import { SongArt } from "./SongArt";
import { openedLabel } from "./songTiles";
import { CloseIcon, PlayIcon } from "../icons";

interface SongTileProps {
  song: SavedSong;
  nowMs: number;
  onOpen: (song: SavedSong) => void;
  onRemove: (song: SavedSong) => void;
}

export function SongTile({ song, nowMs, onOpen, onRemove }: SongTileProps) {
  return (
    <li className="tile">
      <button
        type="button"
        className="tile-open"
        aria-label={`Open ${song.track} by ${song.artist}`}
        onClick={() => {
          onOpen(song);
        }}
      >
        <SongArt track={song.track} videoId={song.videoId}>
          <span className="tile-play" aria-hidden="true">
            <PlayIcon />
          </span>
        </SongArt>
        <span lang="ja" className="tile-title">
          {song.track}
        </span>
        <span className="tile-meta">{song.artist}</span>
        <span className="tile-meta">
          {openedLabel(song.lastOpenedAt, nowMs)}
        </span>
      </button>
      <button
        type="button"
        className="tile-remove icon-button"
        aria-label={`Remove ${song.track}`}
        onClick={() => {
          onRemove(song);
        }}
      >
        <CloseIcon />
      </button>
    </li>
  );
}
