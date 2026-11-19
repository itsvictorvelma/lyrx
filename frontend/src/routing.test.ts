// Checks how addresses map to pages: the library, a song, and anything unknown.
import { expect, test } from "vitest";
import { parseRoute, songPath } from "./routing";

test("AC-6: / is the library and /song/{id} is that song", () => {
  expect(parseRoute("/")).toEqual({ page: "library" });
  expect(parseRoute("/song/101")).toEqual({ page: "song", id: 101 });
  expect(parseRoute("/song/101/")).toEqual({ page: "song", id: 101 });
  expect(songPath(101)).toBe("/song/101");
});

test("AC-6: an unknown or out-of-range address is the library", () => {
  for (const path of [
    "/song/0",
    "/song/-1",
    "/song/1.5",
    "/song/abc",
    "/song/0101",
    "/song/12345678901234567890",
    "/songs/1",
    "/song/1/extra",
  ]) {
    expect(parseRoute(path)).toEqual({ page: "library" });
  }
});
