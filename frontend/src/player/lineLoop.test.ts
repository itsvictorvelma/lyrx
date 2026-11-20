// Checks where a looped line starts and ends in the audio.
import { expect, test } from "vitest";
import { loopRange } from "./lineLoop";
import type { Line } from "../types";

function line(index: number, startMs: number | null): Line {
  const original = startMs === null ? "" : "歌";
  return {
    index,
    original,
    hiragana: "",
    romaji: "",
    english: "",
    startMs,
  };
}

// A verse gap (index 2) sits between the second and third timed lines.
const LINES = [line(0, 1000), line(1, 4000), line(2, null), line(3, 9000)];

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
