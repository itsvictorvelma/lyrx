// What a library tile shows (thumbnail, title colour, "Opened …"), the sort orders, the filter.
import { VIDEO_ID } from "../player/playback";
import type { SavedSong } from "../types";

export type SortOrder = "recent" | "title" | "artist";

const DAY_MS = 24 * 60 * 60 * 1000;

// YouTube's medium thumbnail, only for an id that passes the video-id pattern.
export function thumbnailUrl(videoId: string | null): string | null {
  return videoId !== null && VIDEO_ID.test(videoId)
    ? `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`
    : null;
}

// A hue from 0 to 359 that is always the same for the same title.
export function titleHue(title: string): number {
  let hash = 0;
  for (const character of title) {
    hash = (hash * 31 + (character.codePointAt(0) ?? 0)) % 360;
  }
  return hash;
}

// The first character of the title, whole even when it is outside the basic plane.
export function firstCharacter(title: string): string {
  return Array.from(title.trim())[0] ?? "♪";
}

// "Opened today", "Opened yesterday", or "Opened 5 days ago", by calendar day.
export function openedLabel(openedAtMs: number, nowMs: number): string {
  const startOfToday = new Date(nowMs).setHours(0, 0, 0, 0);
  const startOfOpenedDay = new Date(openedAtMs).setHours(0, 0, 0, 0);
  const days = Math.max(
    0,
    Math.round((startOfToday - startOfOpenedDay) / DAY_MS),
  );
  if (days === 0) {
    return "Opened today";
  }
  return days === 1 ? "Opened yesterday" : `Opened ${String(days)} days ago`;
}

export function sortSongs(songs: SavedSong[], order: SortOrder): SavedSong[] {
  const sorted = [...songs];
  if (order === "recent") {
    sorted.sort((a, b) => b.lastOpenedAt - a.lastOpenedAt);
  } else if (order === "title") {
    sorted.sort((a, b) => a.track.localeCompare(b.track, "ja"));
  } else {
    sorted.sort(
      (a, b) =>
        a.artist.localeCompare(b.artist, "ja") ||
        a.track.localeCompare(b.track, "ja"),
    );
  }
  return sorted;
}

// Songs whose title or artist holds the text, ignoring letter case; all songs for blank text.
export function filterSongs(songs: SavedSong[], text: string): SavedSong[] {
  const wanted = text.trim().toLocaleLowerCase();
  if (wanted === "") {
    return songs;
  }
  return songs.filter(
    (song) =>
      song.track.toLocaleLowerCase().includes(wanted) ||
      song.artist.toLocaleLowerCase().includes(wanted),
  );
}
