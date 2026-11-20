// Checks the library page: order and sorting, thumbnails or a first character, empty state, filter.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import type { SavedSong } from "../types";
import {
  EMPTY_LIBRARY_HINT,
  EMPTY_LIBRARY_TEXT,
  FILTER_SHOWN_ABOVE,
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
    offsetMs: 0,
    lastOpenedAt: 1000,
  },
  {
    id: 2,
    track: "雨の夜",
    artist: "アオ",
    album: "",
    durationSeconds: 200,
    videoId: null,
    offsetMs: 0,
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

function manySongs(count: number): SavedSong[] {
  return Array.from({ length: count }, (_, at) => ({
    id: at + 1,
    track: at === 0 ? "Star Road" : `歌 ${String(at + 1)}`,
    artist: at === 1 ? "Aoi" : "ミナト",
    album: "",
    durationSeconds: 200,
    videoId: null,
    offsetMs: 0,
    lastOpenedAt: at,
  }));
}

test("spec 025 AC-6: the filter shows above 8 songs, matches title or artist, and says when none match", async () => {
  const user = userEvent.setup();
  const { rerender } = render(
    <LibraryPage
      songs={manySongs(FILTER_SHOWN_ABOVE)}
      onOpen={vi.fn()}
      onRemove={vi.fn()}
    />,
  );
  expect(screen.queryByLabelText("Filter your songs")).toBeNull();

  rerender(
    <LibraryPage
      songs={manySongs(FILTER_SHOWN_ABOVE + 1)}
      onOpen={vi.fn()}
      onRemove={vi.fn()}
    />,
  );
  const filter = screen.getByLabelText("Filter your songs");
  await user.type(filter, "STAR");
  expect(screen.getAllByRole("listitem")).toHaveLength(1);
  await user.clear(filter);
  await user.type(filter, "aoi");
  expect(screen.getAllByRole("listitem")).toHaveLength(1);
  await user.clear(filter);
  await user.type(filter, "nothing");
  expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  expect(screen.getByText('No songs match "nothing".')).toBeTruthy();

  // Down to 8 songs, the box hides and its text no longer hides any song.
  rerender(
    <LibraryPage
      songs={manySongs(FILTER_SHOWN_ABOVE)}
      onOpen={vi.fn()}
      onRemove={vi.fn()}
    />,
  );
  expect(screen.getAllByRole("listitem")).toHaveLength(FILTER_SHOWN_ABOVE);
});
