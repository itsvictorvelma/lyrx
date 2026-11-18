// Checks the playback rules: YouTube links, the line being sung with the sync, and the sync text.
import { expect, test } from "vitest";
import {
  currentLineIndex,
  formatOffset,
  hasTimings,
  nudgeOffset,
  parseVideoId,
} from "./playback";
import type { Line } from "./types";

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
