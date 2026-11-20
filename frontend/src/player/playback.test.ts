// Checks the playback rules: YouTube links, the line being sung with the sync, the sync text,
// looping a line, and the remembered volume.
import { afterEach, describe, expect, test } from "vitest";
import {
  currentLineIndex,
  formatOffset,
  hasTimings,
  loopRange,
  nextSpeed,
  nudgeOffset,
  parseVideoId,
  storedVolume,
  storeVolume,
  toggledVolume,
  youTubeSearchUrl,
} from "./playback";
import type { Line } from "../types";

const ID = "abcDEF12_-z";

test.each([
  `https://www.youtube.com/watch?v=${ID}`,
  `https://youtube.com/watch?v=${ID}&t=42s`,
  `https://m.youtube.com/watch?v=${ID}`,
  `https://youtu.be/${ID}`,
  `https://youtu.be/${ID}?si=share`,
  `https://music.youtube.com/watch?v=${ID}&list=x`,
  `https://www.youtube.com/shorts/${ID}`,
  `  https://youtu.be/${ID}  `,
])("AC-7: %s gives the video id", (link) => {
  expect(parseVideoId(link)).toBe(ID);
});

test.each([
  "",
  "not a link",
  `https://vimeo.com/${ID}`,
  `https://youtube.com.evil.example/watch?v=${ID}`,
  `https://www.youtube.com/watch?v=short`,
  `https://www.youtube.com/watch?v=${ID}x`,
  `https://www.youtube.com/channel/${ID}`,
  `javascript:alert("${ID}")`,
  `ftp://youtu.be/${ID}`,
])("AC-7: %s is not a YouTube video link", (link) => {
  expect(parseVideoId(link)).toBeNull();
});

function line(index: number, startMs: number | null): Line {
  return {
    index,
    original: startMs === null ? "" : "夜の月",
    hiragana: "",
    romaji: "",
    english: "",
    startMs,
  };
}

const LINES = [line(0, 1000), line(1, 4000), line(2, null), line(3, 9000)];

test("AC-8: the current line is the last one whose start has passed", () => {
  expect(currentLineIndex(LINES, 500, 0)).toBeNull();
  expect(currentLineIndex(LINES, 1000, 0)).toBe(0);
  expect(currentLineIndex(LINES, 8999, 0)).toBe(1);
  expect(currentLineIndex(LINES, 60000, 0)).toBe(3);
});

test("AC-8: a positive offset makes every line come later", () => {
  expect(currentLineIndex(LINES, 4500, 1000)).toBe(0);
  expect(currentLineIndex(LINES, 5000, 1000)).toBe(1);
  expect(currentLineIndex(LINES, 3200, -1000)).toBe(1);
});

test("the sync moves in quarter seconds and stops at 30 s either way", () => {
  expect(nudgeOffset(0, 1)).toBe(250);
  expect(nudgeOffset(0, -1)).toBe(-250);
  expect(nudgeOffset(30000, 1)).toBe(30000);
  expect(nudgeOffset(-30000, -1)).toBe(-30000);
});

test("the sync text always shows its sign and two decimals", () => {
  expect(formatOffset(0)).toBe("+0.00 s");
  expect(formatOffset(500)).toBe("+0.50 s");
  expect(formatOffset(-250)).toBe("−0.25 s");
});

test("a song has timings when any line has a start", () => {
  expect(hasTimings(LINES)).toBe(true);
  expect(hasTimings([line(0, null)])).toBe(false);
});

test("spec 024 AC-1: the speed steps 1 → 0.75 → 0.5 → 1", () => {
  expect(nextSpeed(1)).toBe(0.75);
  expect(nextSpeed(0.75)).toBe(0.5);
  expect(nextSpeed(0.5)).toBe(1);
});

test("spec 024 AC-3: the YouTube search is for the title and artist, URL-encoded", () => {
  expect(youTubeSearchUrl("星の歌 & more", "ミナト")).toBe(
    "https://www.youtube.com/results?search_query=" +
      encodeURIComponent("星の歌 & more ミナト"),
  );
});

test("a loop runs from its line's start to the next timed line's start, past a verse gap", () => {
  expect(loopRange(LINES, 1, 0, 60_000)).toEqual({
    startMs: 4000,
    endMs: 9000,
  });
});

test("the sync offset moves both ends", () => {
  expect(loopRange(LINES, 0, 500, 60_000)).toEqual({
    startMs: 1500,
    endMs: 4500,
  });
});

test("the last line loops to the song's end, or never ends when the length is unknown", () => {
  expect(loopRange(LINES, 3, 0, 60_000)).toEqual({
    startMs: 9000,
    endMs: 60_000,
  });
  expect(loopRange(LINES, 3, 0, null)?.endMs).toBe(Number.POSITIVE_INFINITY);
});

test("a line with no timing has no loop", () => {
  expect(loopRange(LINES, 2, 0, 60_000)).toBeNull();
});

describe("volume", () => {
  afterEach(() => {
    window.localStorage.removeItem("lyrx-volume");
  });

  test("AC-3: a stored level is read back; a missing or broken one means 100", () => {
    expect(storedVolume()).toBe(100);
    storeVolume(35);
    expect(storedVolume()).toBe(35);
    for (const broken of ["", "loud", "-5", "101", "12.5"]) {
      window.localStorage.setItem("lyrx-volume", broken);
      expect(storedVolume()).toBe(100);
    }
  });

  test("AC-2: Mute goes to 0; Unmute brings back the level before, or 100", () => {
    expect(toggledVolume(60, 60)).toBe(0);
    expect(toggledVolume(0, 60)).toBe(60);
    expect(toggledVolume(0, 0)).toBe(100);
  });
});
