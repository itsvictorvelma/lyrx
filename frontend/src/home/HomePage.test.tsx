// Checks the home page in the whole app: search, first visit or Continue, recent songs, footer, keys.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "../App";
import { SHORTCUT_LIST_TITLE } from "../shortcuts/ShortcutList";
import type { RecentSong, SavedSong } from "../types";
import { SOURCE_CODE_URL } from "./HomePage";

// Invented songs only.
const star: RecentSong = {
  id: 101,
  track: "星の歌",
  artist: "ミナト",
  album: "",
  durationSeconds: 214,
  videoId: null,
};
const rain: RecentSong = { ...star, id: 202, track: "雨の窓", artist: "Kaze" };

let savedSongs: SavedSong[] = [];
let recentSongs: RecentSong[] = [];
let signedInAs: string | null = "mika";
const fakeFetch = vi.fn<typeof fetch>();

function json(body: unknown): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
}

const lines = [
  {
    index: 0,
    original: "星の道",
    hiragana: "ほし の みち",
    romaji: "hoshi no michi",
    english: "The road of stars",
    startMs: null,
  },
];

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  savedSongs = [];
  recentSongs = [];
  signedInAs = "mika";
  fakeFetch.mockReset();
  fakeFetch.mockImplementation((input, init) => {
    const url = typeof input === "string" ? input : "";
    const key = `${init?.method ?? "GET"} ${url}`;
    if (key === "GET /api/account") return json({ username: signedInAs });
    if (key === "GET /api/songs") return json({ songs: savedSongs });
    if (key === "GET /api/recent-songs") return json({ songs: recentSongs });
    if (key === "POST /api/song-search") {
      return json({
        results: [{ ...star, looksJapanese: true, saved: false }],
      });
    }
    if (key === "POST /api/song-versions") {
      return json({
        song: star,
        lines,
        fromLibrary: true,
        playback: { videoId: null, offsetMs: 0 },
        saved: false,
      });
    }
    return Promise.reject(new TypeError(`no fake reply for ${key}`));
  });
  vi.stubGlobal("fetch", fakeFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function saved(song: RecentSong, lastOpenedAt: number): SavedSong {
  return { ...song, offsetMs: 0, lastOpenedAt };
}

test("AC-1: Your songs goes to the library and the wordmark back home", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("link", { name: "Your songs" }));
  expect(window.location.pathname).toBe("/library");
  expect(await screen.findByText("Your songs will show up here.")).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: "Your songs" })
      .getAttribute("aria-current"),
  ).toBe("page");

  await user.click(screen.getByRole("link", { name: /subbed/ }));
  expect(window.location.pathname).toBe("/");
});

test("spec 028 AC-2: the wordmark reads subbed 字幕, with the kanji marked as Japanese", () => {
  render(<App />);

  const wordmark = screen.getByRole("link", { name: "subbed 字幕" });
  expect(within(wordmark).getByText("字幕").getAttribute("lang")).toBe("ja");
});

test("AC-2: home has one search box, the large one, and it finds and opens a song", async () => {
  const user = userEvent.setup();
  render(<App />);

  expect(screen.getAllByRole("search")).toHaveLength(1);
  expect(screen.getByRole("banner").querySelector("form")).toBeNull();
  await user.type(screen.getByLabelText("Song name or artist"), "星の歌");
  await user.click(screen.getByRole("button", { name: "Find" }));

  expect(await screen.findByRole("table")).toBeTruthy();
  expect(window.location.pathname).toBe("/song/101");
});

test("AC-5: a first visit shows the three steps and no Continue card", async () => {
  render(<App />);

  const steps = await screen.findByRole("heading", {
    name: "How Subbed works",
  });
  const list = within(steps.closest("section") ?? document.body);
  expect(list.getAllByRole("listitem")).toHaveLength(3);
  expect(screen.queryByText("Pick up where you left off")).toBeNull();
});

test("AC-5: a returning visitor gets Continue for the latest song and a link to all songs", async () => {
  savedSongs = [saved(star, 1000), saved(rain, 2000)];
  const user = userEvent.setup();
  render(<App />);

  const resume = await screen.findByRole("button", {
    name: "Continue 雨の窓 by Kaze",
  });
  expect(screen.getByRole("link", { name: "All your songs (2)" })).toBeTruthy();
  expect(screen.queryByText("How Subbed works")).toBeNull();

  await user.click(resume);
  expect(window.location.pathname).toBe("/song/202");
});

test("AC-6: Songs already in Subbed lists the recent songs and opens one", async () => {
  recentSongs = [star, rain];
  const user = userEvent.setup();
  render(<App />);

  const heading = await screen.findByRole("heading", {
    name: "Songs already in Subbed",
  });
  const row = within(heading.closest("section") ?? document.body);
  expect(row.getAllByRole("listitem")).toHaveLength(2);

  await user.click(row.getByRole("button", { name: "Open 星の歌 by ミナト" }));
  expect(await screen.findByRole("table")).toBeTruthy();
  expect(window.location.pathname).toBe("/song/101");
});

test("AC-6: with no recent songs the section is hidden", async () => {
  render(<App />);

  await screen.findByRole("heading", { name: "How Subbed works" });
  expect(screen.queryByText("Songs already in Subbed")).toBeNull();
});

test("AC-9: the footer credits LRCLIB, Groq, and Gemini and links the source", () => {
  render(<App />);

  const footer = screen.getByRole("contentinfo");
  expect(footer.textContent).toContain("Lyrics from LRCLIB");
  expect(footer.textContent).toContain("Groq and Gemini");
  expect(
    within(footer)
      .getByRole("link", { name: "Source on GitHub" })
      .getAttribute("href"),
  ).toBe(SOURCE_CODE_URL);
});

test.each(["/", "/library"])(
  "AC-8: on %s, ? shows and hides the shortcut list and / jumps to the search box",
  async (path) => {
    window.history.replaceState(null, "", path);
    const user = userEvent.setup();
    render(<App />);

    await user.keyboard("?");
    const list = screen.getByRole("dialog", { name: SHORTCUT_LIST_TITLE });
    expect(within(list).getByText("Jump to the search box")).toBeTruthy();
    await user.keyboard("?");
    expect(screen.queryByRole("dialog")).toBeNull();

    await user.keyboard("/");
    const search = screen.getByLabelText("Song name or artist");
    expect(document.activeElement).toBe(search);

    // In the field, ? and / are typed, not shortcuts.
    await user.keyboard("?/");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect((search as HTMLInputElement).value).toBe("?/");
  },
);

test("spec 023 AC-1: Home and Your songs are in the header, the current page marked", async () => {
  const user = userEvent.setup();
  render(<App />);
  const current = (name: string) =>
    screen.getByRole("link", { name }).getAttribute("aria-current");

  expect(current("Home")).toBe("page");
  expect(current("Your songs")).toBeNull();

  await user.click(screen.getByRole("link", { name: "Your songs" }));
  expect(current("Home")).toBeNull();
  expect(current("Your songs")).toBe("page");

  await user.click(screen.getByRole("link", { name: "Home" }));
  expect(window.location.pathname).toBe("/");
  expect(current("Home")).toBe("page");

  window.history.replaceState(null, "", "/song/101");
  window.dispatchEvent(new PopStateEvent("popstate"));
  expect(await screen.findByRole("table")).toBeTruthy();
  expect(current("Home")).toBeNull();
  expect(current("Your songs")).toBeNull();
});

test("spec 014 AC-17: a guest's home has no Continue card, and says to sign in to save songs", async () => {
  signedInAs = null;
  savedSongs = [saved(star, 1000)];
  recentSongs = [star];
  render(<App />);

  expect(
    await screen.findByText("to save songs.", { exact: false }),
  ).toBeTruthy();
  expect(screen.queryByRole("button", { name: /^Continue/ })).toBeNull();
  expect(screen.queryByRole("link", { name: /All your songs/ })).toBeNull();
  expect(
    screen.getByRole("heading", { name: "Songs already in Subbed" }),
  ).toBeTruthy();
  const asked = fakeFetch.mock.calls.map(([url]) => url);
  expect(asked).not.toContain("/api/songs");
});

test("spec 014 AC-17: Your songs shows a guest the sign-in prompt", async () => {
  signedInAs = null;
  window.history.replaceState(null, "", "/library");
  const user = userEvent.setup();
  render(<App />);

  expect(
    await screen.findByRole("heading", {
      name: "Sign in to keep your songs here.",
    }),
  ).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(window.location.pathname).toBe("/account");
});
