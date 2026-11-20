// Checks how addresses map to pages, and where Back on a song goes.
import { expect, test, vi } from "vitest";
import { goBack, navigate, parseRoute, songPath } from "./routing";

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

test("spec 025 AC-3: Back goes back after a Lyrx move, and home when the song was the first page", () => {
  const back = vi
    .spyOn(window.history, "back")
    .mockImplementation(() => undefined);
  window.history.replaceState(null, "", "/song/101");
  goBack();
  expect(back).not.toHaveBeenCalled();
  expect(window.location.pathname).toBe("/");

  navigate("/song/202");
  goBack();
  expect(back).toHaveBeenCalledTimes(1);
  back.mockRestore();
});
