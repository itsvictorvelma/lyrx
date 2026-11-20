// Checks how addresses map to pages: home, the library, a song, and anything unknown.
import { expect, test } from "vitest";
import { parseRoute, songPath } from "./routing";

test("spec 021 AC-1: / is home, /library the library, /song/{id} that song", () => {
  expect(parseRoute("/")).toEqual({ page: "home" });
  expect(parseRoute("/library")).toEqual({ page: "library" });
  expect(parseRoute("/library/")).toEqual({ page: "library" });
  expect(parseRoute("/song/101")).toEqual({ page: "song", id: 101 });
  expect(parseRoute("/song/101/")).toEqual({ page: "song", id: 101 });
  expect(songPath(101)).toBe("/song/101");
});

test("spec 021 AC-1: an unknown or out-of-range address is home", () => {
  for (const path of [
    "/song/0",
    "/song/-1",
    "/song/1.5",
    "/song/abc",
    "/song/0101",
    "/song/12345678901234567890",
    "/songs/1",
    "/song/1/extra",
    "/library/1",
  ]) {
    expect(parseRoute(path)).toEqual({ page: "home" });
  }
});
