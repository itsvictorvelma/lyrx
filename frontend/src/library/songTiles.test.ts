// Checks what a library tile shows, the sort orders, and the filter.
import { expect, test } from "vitest";
import type { SavedSong } from "../types";
import {
  filterSongs,
  firstCharacter,
  openedLabel,
  sortSongs,
  thumbnailUrl,
  titleHue,
} from "./songTiles";

// Invented songs only.
function song(
  id: number,
  track: string,
  artist: string,
  lastOpenedAt: number,
): SavedSong {
  return {
    id,
    track,
    artist,
    album: "",
    durationSeconds: 200,
    videoId: null,
    offsetMs: 0,
    lastOpenedAt,
  };
}

test("AC-3: a thumbnail is built only from a valid video id", () => {
  expect(thumbnailUrl("abcDEF12_-z")).toBe(
    "https://i.ytimg.com/vi/abcDEF12_-z/mqdefault.jpg",
  );
  expect(thumbnailUrl(null)).toBeNull();
  expect(thumbnailUrl("../../evil")).toBeNull();
  expect(thumbnailUrl("abcDEF12_-z/x")).toBeNull();
});

test("AC-3: a title always gets the same hue, and the first character is whole", () => {
  expect(titleHue("星の歌")).toBe(titleHue("星の歌"));
  expect(titleHue("星の歌")).toBeGreaterThanOrEqual(0);
  expect(titleHue("星の歌")).toBeLessThan(360);
  expect(firstCharacter("星の歌")).toBe("星");
  expect(firstCharacter("𠮷野家")).toBe("𠮷");
});

test("opened labels count calendar days", () => {
  const now = new Date(2026, 10, 18, 9, 0).getTime();
  expect(openedLabel(new Date(2026, 10, 18, 1, 0).getTime(), now)).toBe(
    "Opened today",
  );
  expect(openedLabel(new Date(2026, 10, 17, 23, 0).getTime(), now)).toBe(
    "Opened yesterday",
  );
  expect(openedLabel(new Date(2026, 10, 13, 12, 0).getTime(), now)).toBe(
    "Opened 5 days ago",
  );
});

test("AC-1: songs sort by recent, title, and artist", () => {
  const songs = [
    song(1, "風の道", "ミナト", 100),
    song(2, "雨の夜", "アオ", 300),
    song(3, "朝の窓", "ミナト", 200),
  ];

  expect(sortSongs(songs, "recent").map((s) => s.id)).toEqual([2, 3, 1]);
  expect(sortSongs(songs, "title").map((s) => s.track)).toEqual(
    [...songs.map((s) => s.track)].sort((a, b) => a.localeCompare(b, "ja")),
  );
  expect(sortSongs(songs, "artist").map((s) => s.artist)).toEqual([
    "アオ",
    "ミナト",
    "ミナト",
  ]);
});

test("spec 025 AC-6: the filter matches title or artist, ignoring letter case", () => {
  const songs = [
    song(1, "Star Road", "ミナト", 1),
    song(2, "雨の夜", "Aoi", 2),
  ];
  expect(filterSongs(songs, "star").map((s) => s.id)).toEqual([1]);
  expect(filterSongs(songs, " AOI ").map((s) => s.id)).toEqual([2]);
  expect(filterSongs(songs, "雨").map((s) => s.id)).toEqual([2]);
  expect(filterSongs(songs, "  ")).toHaveLength(2);
});
