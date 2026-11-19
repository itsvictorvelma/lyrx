// One library tile: the art (thumbnail or first character), title, artist, last opened, Remove.
import type { CSSProperties } from "react";
import type { SavedSong } from "../lyrics/types";
import {
  firstCharacter,
  openedLabel,
  thumbnailUrl,
  titleHue,
} from "./songTiles";

interface SongTileProps {
  song: SavedSong;
  nowMs: number;
  onOpen: (song: SavedSong) => void;
  onRemove: (song: SavedSong) => void;
}

export function SongTile({ song, nowMs, onOpen, onRemove }: SongTileProps) {
  const thumbnail = thumbnailUrl(song.videoId);
  const hue = { "--tile-hue": titleHue(song.track) } as CSSProperties;

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
        <span className="tile-art" style={hue}>
          {thumbnail === null ? (
            <span lang="ja" className="tile-glyph" aria-hidden="true">
              {firstCharacter(song.track)}
            </span>
          ) : (
            <img
              src={thumbnail}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
            />
          )}
          <span className="tile-play" aria-hidden="true">
            <svg viewBox="0 0 24 24" className="icon icon-filled">
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
        </span>
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
        <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </li>
  );
}
