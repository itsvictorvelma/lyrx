// Checks the whole page: find, open the best match, switch, saved songs, errors, timing.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App, FALLBACK_MESSAGE, timingText } from "./App";
import type { Line, SearchResult, Song } from "./lyrics/types";

// A fake server: each address answers from its own queue; the saved list is empty by default.
const queues = new Map<string, Response[]>();
const fakeFetch = vi.fn<typeof fetch>();

function urlOf(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }
  return input instanceof URL ? input.href : input.url;
}

function respond(key: string, ...responses: Response[]) {
  queues.set(key, [...(queues.get(key) ?? []), ...responses]);
}

beforeEach(() => {
  queues.clear();
  fakeFetch.mockReset();
  fakeFetch.mockImplementation((input, init) => {
    const key = `${init?.method ?? "GET"} ${urlOf(input)}`;
    const next = queues.get(key)?.shift();
    if (next !== undefined) {
      return Promise.resolve(next);
    }
    if (key === "GET /api/songs") {
      return Promise.resolve(jsonResponse(200, { songs: [] }));
    }
    return Promise.reject(new TypeError(`no fake reply for ${key}`));
  });
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
  saved: false,
};
const liveMatch: SearchResult = {
  id: 202,
  track: "星の歌 (live)",
  artist: "ミナト",
  album: "",
  durationSeconds: 250,
  looksJapanese: true,
  saved: true,
};
const otherMatch: SearchResult = {
  id: 303,
  track: "Star Song",
  artist: "Nika",
  album: "",
  durationSeconds: 199,
  looksJapanese: false,
  saved: false,
};
const results = [bestMatch, liveMatch, otherMatch];

const firstLine: Line = {
  index: 0,
  original: "星の道",
  hiragana: "ほし の みち",
  romaji: "hoshi no michi",
  english: "The road of stars",
  startMs: null,
};
const lines: Line[] = [
  firstLine,
  {
    index: 1,
    original: "",
    hiragana: "",
    romaji: "",
    english: "",
    startMs: null,
  },
  {
    index: 2,
    original: "風が歌う",
    hiragana: "かぜ が うたう",
    romaji: "kaze ga utau",
    english: "The wind sings",
    startMs: null,
  },
];

function jsonResponse(status: number, body: unknown): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
  });
}

function asSong(result: SearchResult): Song {
  return {
    id: result.id,
    track: result.track,
    artist: result.artist,
    album: result.album,
    durationSeconds: result.durationSeconds,
  };
}

function songReply(
  result: SearchResult,
  songLines: Line[] = lines,
  fromLibrary = false,
) {
  return jsonResponse(200, {
    song: asSong(result),
    lines: songLines,
    fromLibrary,
    playback: { videoId: null, offsetMs: 0 },
  });
}

function bodyOf(method: string, url: string): unknown {
  const call = fakeFetch.mock.calls.find(
    ([input, init]) => urlOf(input) === url && init?.method === method,
  );
  const body = call?.[1]?.body;
  return typeof body === "string" ? JSON.parse(body) : undefined;
}

async function findSong(query = "星の歌") {
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("Song name or artist"), query);
  await user.click(screen.getByRole("button", { name: "Find" }));
  return user;
}

test("Find searches, opens the best match, and shows a four-column table", async () => {
  respond("POST /api/song-search", jsonResponse(200, { results }));
  respond("POST /api/song-versions", songReply(bestMatch));

  await findSong();

  const table = await screen.findByRole("table");
  expect(bodyOf("POST", "/api/song-search")).toEqual({ query: "星の歌" });
  expect(bodyOf("POST", "/api/song-versions")).toEqual({ id: 101 });
  expect(screen.getByText("(lyrics from LRCLIB)")).toBeTruthy();
  const headers = within(table)
    .getAllByRole("columnheader")
    .map((cell) => cell.textContent);
  expect(headers).toEqual(["Original", "Hiragana", "Romaji", "English"]);
  // A header row and one row per lyric line: the blank line is a verse gap, not a row.
  expect(within(table).getAllByRole("row")).toHaveLength(3);
  expect(within(table).getByText("kaze ga utau")).toBeTruthy();
});

test("picking another match opens that song; results say Saved and Not Japanese", async () => {
  respond("POST /api/song-search", jsonResponse(200, { results }));
  respond(
    "POST /api/song-versions",
    songReply(bestMatch),
    songReply(liveMatch, [{ ...firstLine, english: "Live road" }]),
  );
  const user = await findSong();
  await screen.findByRole("table");

  await user.click(screen.getByText("Not this song?"));
  expect(screen.getByText("Not Japanese")).toBeTruthy();
  expect(screen.getByText("Saved")).toBeTruthy();
  await user.click(
    screen.getByRole("button", { name: "星の歌 (live) — ミナト, 4:10" }),
  );

  expect(await screen.findByText("Live road")).toBeTruthy();
});

test("Your songs lists saved songs; clicking one opens it from the library", async () => {
  respond("GET /api/songs", jsonResponse(200, { songs: [asSong(bestMatch)] }));
  respond("POST /api/song-versions", songReply(bestMatch, lines, true));
  const user = userEvent.setup();
  render(<App />);

  const list = await screen.findByRole("region", { name: "Your songs" });
  await user.click(
    within(list).getByRole("button", { name: "星の歌 — ミナト, 3:34" }),
  );

  await screen.findByRole("table");
  expect(
    screen.getByText(/^Opened from your songs in \d+\.\d s$/),
  ).toBeTruthy();
});

test("Remove takes a song off the list", async () => {
  respond(
    "GET /api/songs",
    jsonResponse(200, { songs: [asSong(bestMatch), asSong(liveMatch)] }),
  );
  respond("DELETE /api/songs/101", jsonResponse(204, null));
  const user = userEvent.setup();
  render(<App />);

  await user.click(
    await screen.findByRole("button", { name: "Remove 星の歌" }),
  );

  expect(screen.queryByRole("button", { name: "Remove 星の歌" })).toBeNull();
  expect(
    fakeFetch.mock.calls.some(([, init]) => init?.method === "DELETE"),
  ).toBe(true);
  expect(
    screen.getByRole("button", { name: "Remove 星の歌 (live)" }),
  ).toBeTruthy();
});

test("no song found shows the server's hint and there is no paste form", async () => {
  respond(
    "POST /api/song-search",
    jsonResponse(404, {
      code: "song_not_found",
      message: "No song found for that name. Try the title and artist.",
    }),
  );

  await findSong("nothing");

  expect((await screen.findByRole("alert")).textContent).toContain(
    "Try the title and artist.",
  );
  expect(screen.queryByText(/paste/i)).toBeNull();
  expect(screen.queryByRole("textbox", { name: /lyrics/i })).toBeNull();
});

test("a malformed 200 reply shows the fallback message", async () => {
  respond(
    "POST /api/song-search",
    jsonResponse(200, { results: [{ id: "x" }] }),
  );

  await findSong();

  expect((await screen.findByRole("alert")).textContent).toContain(
    FALLBACK_MESSAGE,
  );
});

test("server text is rendered as text, never HTML", async () => {
  respond("POST /api/song-search", jsonResponse(200, { results: [bestMatch] }));
  respond(
    "POST /api/song-versions",
    songReply(bestMatch, [{ ...firstLine, english: "<b>bold</b>" }]),
  );

  await findSong();

  expect(await screen.findByText("<b>bold</b>")).toBeTruthy();
  expect(document.querySelector("b")).toBeNull();
});

test("the server being down says so", async () => {
  await findSong();

  expect((await screen.findByRole("alert")).textContent).toContain(
    "Could not reach the Lyrx server.",
  );
});

test("a line the translator could not do says Not available", async () => {
  respond("POST /api/song-search", jsonResponse(200, { results: [bestMatch] }));
  respond(
    "POST /api/song-versions",
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
  const pending = new Promise<Response>((resolve) => {
    finish = resolve;
  });
  const answerByAddress = fakeFetch.getMockImplementation();
  fakeFetch.mockImplementation((input, init) =>
    urlOf(input) === "/api/song-search"
      ? pending
      : (answerByAddress?.(input, init) ?? Promise.reject(new TypeError())),
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
  respond("POST /api/song-search", jsonResponse(200, { results: [bestMatch] }));
  respond("POST /api/song-versions", songReply(bestMatch));

  await findSong();

  await screen.findByRole("table");
  expect(
    screen.getByText(/^Found in \d+\.\d s · versions in \d+\.\d s$/),
  ).toBeTruthy();
});

test("timingText formats milliseconds as seconds", () => {
  expect(
    timingText({ fromLibrary: false, findMs: 420, versionsMs: 12345 }),
  ).toBe("Found in 0.4 s · versions in 12.3 s");
  expect(timingText({ fromLibrary: false, versionsMs: 900 })).toBe(
    "Versions in 0.9 s",
  );
  expect(timingText({ fromLibrary: true, versionsMs: 30 })).toBe(
    "Opened from your songs in 0.0 s",
  );
});

test("removing a song clears its Saved mark in the search results", async () => {
  // Once when the page opens, once more after the song opens.
  respond(
    "GET /api/songs",
    jsonResponse(200, { songs: [asSong(liveMatch)] }),
    jsonResponse(200, { songs: [asSong(liveMatch)] }),
  );
  respond("POST /api/song-search", jsonResponse(200, { results }));
  respond("POST /api/song-versions", songReply(bestMatch));
  respond("DELETE /api/songs/202", jsonResponse(204, null));
  const user = await findSong();
  await screen.findByRole("table");
  await user.click(screen.getByText("Not this song?"));
  expect(screen.getByText("Saved")).toBeTruthy();

  await user.click(
    screen.getByRole("button", { name: "Remove 星の歌 (live)" }),
  );

  expect(screen.queryByText("Saved")).toBeNull();
});
