// Checks the library page: tile order and sorting, thumbnails or a first character, the empty state.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import type { SavedSong } from "../lyrics/types";
import {
  EMPTY_LIBRARY_HINT,
  EMPTY_LIBRARY_TEXT,
  LibraryPage,
} from "./LibraryPage";

// Invented songs only.
const songs: SavedSong[] = [
  {
    id: 1,
    track: "風の道",
    artist: "ミナト",
    album: "",
    durationSeconds: 200,
    videoId: "abcDEF12_-z",
    lastOpenedAt: 1000,
  },
  {
    id: 2,
    track: "雨の夜",
    artist: "アオ",
    album: "",
    durationSeconds: 200,
    videoId: null,
    lastOpenedAt: 3000,
  },
];

function renderLibrary(list: SavedSong[]) {
  render(<LibraryPage songs={list} onOpen={vi.fn()} onRemove={vi.fn()} />);
}

function tileNames(): string[] {
  return screen
    .getAllByRole("button", { name: /^Open / })
    .map((button) => button.getAttribute("aria-label") ?? "");
}

test("AC-1: tiles are most recently opened first; A–Z and Artist reorder them", async () => {
  const user = userEvent.setup();
  renderLibrary(songs);

  expect(tileNames()).toEqual(["Open 雨の夜 by アオ", "Open 風の道 by ミナト"]);
  await user.click(screen.getByRole("button", { name: "Artist" }));
  expect(tileNames()).toEqual(["Open 雨の夜 by アオ", "Open 風の道 by ミナト"]);
  expect(
    screen.getByRole("button", { name: "Artist" }).getAttribute("aria-pressed"),
  ).toBe("true");
  await user.click(screen.getByRole("button", { name: "A–Z" }));
  const byTitle = [...songs].sort((a, b) =>
    a.track.localeCompare(b.track, "ja"),
  );
  expect(tileNames()).toEqual(
    byTitle.map((s) => `Open ${s.track} by ${s.artist}`),
  );
});

test("AC-2: with no saved songs, the library welcomes you with an example", () => {
  renderLibrary([]);

  expect(
    screen.getByRole("heading", { name: EMPTY_LIBRARY_TEXT }),
  ).toBeTruthy();
  expect(screen.getByText(EMPTY_LIBRARY_HINT)).toBeTruthy();
});

test("AC-3: a linked song shows its thumbnail; another shows its first character", () => {
  renderLibrary(songs);

  const linked = screen.getByRole("button", { name: "Open 風の道 by ミナト" });
  expect(linked.querySelector("img")?.getAttribute("src")).toBe(
    "https://i.ytimg.com/vi/abcDEF12_-z/mqdefault.jpg",
  );
  const plain = screen.getByRole("button", { name: "Open 雨の夜 by アオ" });
  expect(plain.querySelector("img")).toBeNull();
  expect(within(plain).getAllByText("雨")[0]).toBeTruthy();
});
