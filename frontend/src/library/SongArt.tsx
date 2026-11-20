// A song's square art: its YouTube thumbnail, or its first character on a hue from its title.
import type { CSSProperties, ReactNode } from "react";
import { firstCharacter, thumbnailUrl, titleHue } from "./songTiles";

interface SongArtProps {
  track: string;
  videoId: string | null;
  // Shown over the art, such as the library's play mark.
  children?: ReactNode;
}

export function SongArt({ track, videoId, children }: SongArtProps) {
  const thumbnail = thumbnailUrl(videoId);
  const hue = { "--tile-hue": titleHue(track) } as CSSProperties;

  return (
    <span className="tile-art" style={hue}>
      {thumbnail === null ? (
        <span lang="ja" className="tile-glyph" aria-hidden="true">
          {firstCharacter(track)}
        </span>
      ) : (
        <img
          src={thumbnail}
          alt=""
          loading="lazy"
          referrerPolicy="no-referrer"
        />
      )}
      {children}
    </span>
  );
}
