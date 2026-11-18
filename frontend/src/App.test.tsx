// Checks the whole page (AC-14 to AC-17): find, open the best match, switch, paste, errors.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App, FALLBACK_MESSAGE, timingText } from "./App";
import type { Line, SearchResult } from "./lyrics/types";

const fakeFetch = vi.fn<typeof fetch>();

beforeEach(() => {
  fakeFetch.mockReset();
  vi.stubGlobal("fetch", fakeFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// Invented songs and lyrics only.
const bestMatch: SearchResult = {
  id: 101,
  track: "星の歌",
  artist: "ミナト",
  album: "夜の窓",
  durationSeconds: 214,
  looksJapanese: true,
};
const liveMatch: SearchResult = {
  id: 202,
  track: "星の歌 (live)",
  artist: "ミナト",
  album: "",
  durationSeconds: 250,
  looksJapanese: true,
};
const otherMatch: SearchResult = {
  id: 303,
  track: "Star Song",
  artist: "Nika",
  album: "",
  durationSeconds: 199,
  looksJapanese: false,
};
const results = [bestMatch, liveMatch, otherMatch];

const firstLine: Line = {
  index: 0,
  original: "星の道",
  hiragana: "ほし の みち",
  romaji: "hoshi no michi",
  english: "The road of stars",
};
const lines: Line[] = [
  firstLine,
  { index: 1, original: "", hiragana: "", romaji: "", english: "" },
  {
    index: 2,
    original: "風が歌う",
    hiragana: "かぜ が うたう",
    romaji: "kaze ga utau",
    english: "The wind sings",
  },
];

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status });
}

function songReply(result: SearchResult, songLines: Line[] = lines) {
  const song = {
    id: result.id,
    track: result.track,
    artist: result.artist,
    album: result.album,
    durationSeconds: result.durationSeconds,
  };
  return jsonResponse(200, { song, lines: songLines });
}

function requestBody(call: number): unknown {
  const body = fakeFetch.mock.calls[call]?.[1]?.body;
  return typeof body === "string" ? JSON.parse(body) : undefined;
}

async function findSong(query = "星の歌") {
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("Song name or artist"), query);
  await user.click(screen.getByRole("button", { name: "Find" }));
  return user;
}

test("AC-14: Find searches, opens the best match, and shows a four-column table", async () => {
  fakeFetch
    .mockResolvedValueOnce(jsonResponse(200, { results }))
    .mockResolvedValueOnce(songReply(bestMatch));

  await findSong();

  const table = await screen.findByRole("table");
  expect(fakeFetch.mock.calls[0]?.[0]).toBe("/api/song-search");
  expect(requestBody(0)).toEqual({ query: "星の歌" });
  expect(fakeFetch.mock.calls[1]?.[0]).toBe("/api/song-versions");
  expect(requestBody(1)).toEqual({ id: 101 });
  expect(screen.getByText("(lyrics from LRCLIB)")).toBeTruthy();
  const headers = within(table)
    .getAllByRole("columnheader")
    .map((cell) => cell.textContent);
  expect(headers).toEqual(["Original", "Hiragana", "Romaji", "English"]);
  // A header row and one row per lyric line: the blank line is a verse gap, not a row.
  expect(within(table).getAllByRole("row")).toHaveLength(3);
  expect(within(table).getByText("kaze ga utau")).toBeTruthy();
});

test("AC-15: picking another match opens that song instead", async () => {
  fakeFetch
    .mockResolvedValueOnce(jsonResponse(200, { results }))
    .mockResolvedValueOnce(songReply(bestMatch))
    .mockResolvedValueOnce(
      songReply(liveMatch, [{ ...firstLine, english: "Live road" }]),
    );
  const user = await findSong();
  await screen.findByRole("table");

  await user.click(screen.getByText("Not this song?"));
  expect(screen.getByText("Not Japanese")).toBeTruthy();
  await user.click(
    screen.getByRole("button", { name: "星の歌 (live) — ミナト, 4:10" }),
  );

  expect(await screen.findByText("Live road")).toBeTruthy();
  expect(requestBody(2)).toEqual({ id: 202 });
});

test("AC-16: no song found shows the message, and the paste form gives the same table", async () => {
  fakeFetch
    .mockResolvedValueOnce(
      jsonResponse(404, {
        code: "song_not_found",
        message: "No song found for that name.",
      }),
    )
    .mockResolvedValueOnce(jsonResponse(200, { lines }));
  const user = await findSong("nothing");

  expect((await screen.findByRole("alert")).textContent).toContain(
    "No song found for that name.",
  );
  await user.click(
    screen.getByRole("button", { name: "Paste the lyrics instead" }),
  );
  await user.type(screen.getByLabelText("Japanese lyrics"), "星の道");
  await user.click(screen.getByRole("button", { name: "Show the versions" }));

  expect(await screen.findByRole("table")).toBeTruthy();
  expect(fakeFetch.mock.calls[1]?.[0]).toBe("/api/versions");
});

test("AC-17: an error reply shows its message", async () => {
  fakeFetch.mockResolvedValueOnce(
    jsonResponse(429, {
      code: "translation_rate_limited",
      message: "The free Gemini limit was reached. Try again later.",
    }),
  );

  await findSong();

  expect((await screen.findByRole("alert")).textContent).toContain(
    "The free Gemini limit was reached.",
  );
});

test("AC-17: a malformed 200 reply shows the fallback message", async () => {
  fakeFetch.mockResolvedValueOnce(
    jsonResponse(200, { results: [{ id: "x" }] }),
  );

  await findSong();

  expect((await screen.findByRole("alert")).textContent).toContain(
    FALLBACK_MESSAGE,
  );
});

test("AC-17: server text is rendered as text, never HTML", async () => {
  fakeFetch
    .mockResolvedValueOnce(jsonResponse(200, { results: [bestMatch] }))
    .mockResolvedValueOnce(
      songReply(bestMatch, [{ ...firstLine, english: "<b>bold</b>" }]),
    );

  await findSong();

  expect(await screen.findByText("<b>bold</b>")).toBeTruthy();
  expect(document.querySelector("b")).toBeNull();
});

test("the server being down says so", async () => {
  fakeFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

  await findSong();

  expect((await screen.findByRole("alert")).textContent).toContain(
    "Could not reach the Lyrx server.",
  );
});

test("a line Gemini could not do says Not available", async () => {
  fakeFetch
    .mockResolvedValueOnce(jsonResponse(200, { results: [bestMatch] }))
    .mockResolvedValueOnce(
      songReply(bestMatch, [
        { ...firstLine, hiragana: "", romaji: "", english: "" },
      ]),
    );

  await findSong();

  await screen.findByRole("table");
  expect(screen.getAllByText("Not available")).toHaveLength(3);
});

test("the waiting line counts the seconds", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  let finish: (response: Response) => void = () => undefined;
  fakeFetch.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );

  await findSong();
  await vi.advanceTimersByTimeAsync(3000);

  const status = screen.getByRole("status");
  expect(status.textContent).toContain("Finding the song…");
  expect(status.textContent).toContain("3 s");
  finish(jsonResponse(200, { results: [] }));
  vi.useRealTimers();
});

test("the timing line says how long finding and the versions took", async () => {
  fakeFetch
    .mockResolvedValueOnce(jsonResponse(200, { results: [bestMatch] }))
    .mockResolvedValueOnce(songReply(bestMatch));

  await findSong();

  await screen.findByRole("table");
  expect(
    screen.getByText(/^Found in \d+\.\d s · versions in \d+\.\d s$/),
  ).toBeTruthy();
});

test("timingText formats milliseconds as seconds", () => {
  expect(timingText({ lines: [], findMs: 420, versionsMs: 12345 })).toBe(
    "Found in 0.4 s · versions in 12.3 s",
  );
  expect(timingText({ lines: [], versionsMs: 900 })).toBe("Versions in 0.9 s");
});
