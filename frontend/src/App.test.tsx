// Checks the whole app: search, song addresses and Back, home and the library, Remove, Focus, errors.
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App, FALLBACK_MESSAGE, timingText } from "./App";
import type { Line, SavedSong, SearchResult, Song } from "./lyrics/types";
import { navigate } from "./routing";

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
  window.history.replaceState(null, "", "/");
  vi.spyOn(window, "confirm").mockReturnValue(true);
  queues.clear();
  fakeFetch.mockReset();
  fakeFetch.mockImplementation((input, init) => {
    const key = `${init?.method ?? "GET"} ${urlOf(input)}`;
    const next = queues.get(key)?.shift();
    if (next !== undefined) {
      return Promise.resolve(next);
    }
    if (key === "GET /api/songs" || key === "GET /api/recent-songs") {
      return Promise.resolve(jsonResponse(200, { songs: [] }));
    }
    return Promise.reject(new TypeError(`no fake reply for ${key}`));
  });
  vi.stubGlobal("fetch", fakeFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const HOME_TITLE = "Read any Japanese song, line by line.";

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

function asSaved(
  result: SearchResult,
  lastOpenedAt = Date.now(),
  videoId: string | null = null,
): SavedSong {
  return { ...asSong(result), videoId, lastOpenedAt };
}

function songReply(
  result: SearchResult,
  songLines: Line[] = lines,
  fromLibrary = false,
  saved = fromLibrary,
) {
  return jsonResponse(200, {
    song: asSong(result),
    lines: songLines,
    fromLibrary,
    playback: { videoId: null, offsetMs: 0 },
    saved,
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

test("AC-5: Find searches, opens the best match at its address, in four columns", async () => {
  respond("POST /api/song-search", jsonResponse(200, { results }));
  respond("POST /api/song-versions", songReply(bestMatch));

  await findSong();

  const table = await screen.findByRole("table");
  expect(window.location.pathname).toBe("/song/101");
  expect(bodyOf("POST", "/api/song-search")).toEqual({ query: "星の歌" });
  expect(bodyOf("POST", "/api/song-versions")).toEqual({ id: 101 });
  expect(screen.getByRole("heading", { name: "星の歌" })).toBeTruthy();
  const headers = within(table)
    .getAllByRole("columnheader")
    .map((cell) => cell.textContent);
  expect(headers).toEqual(["Original", "Hiragana", "Romaji", "English"]);
  // A header row and one row per lyric line: the blank line is a verse gap, not a row.
  expect(within(table).getAllByRole("row")).toHaveLength(3);
  expect(within(table).getByText("kaze ga utau")).toBeTruthy();
});

test("Not this one? opens another match; results say Saved and Not Japanese", async () => {
  respond("POST /api/song-search", jsonResponse(200, { results }));
  respond(
    "POST /api/song-versions",
    songReply(bestMatch),
    songReply(liveMatch, [{ ...firstLine, english: "Live road" }]),
  );
  const user = await findSong();
  await screen.findByRole("table");

  await user.click(screen.getByText("Not this one?"));
  expect(screen.getByText("Not Japanese")).toBeTruthy();
  expect(screen.getByText("Saved")).toBeTruthy();
  await user.click(
    screen.getByRole("button", { name: "星の歌 (live) — ミナト, 4:10" }),
  );

  expect(await screen.findByText("Live road")).toBeTruthy();
  expect(window.location.pathname).toBe("/song/202");
});

test("AC-1: clicking a library tile opens the song from your songs", async () => {
  window.history.replaceState(null, "", "/library");
  respond("GET /api/songs", jsonResponse(200, { songs: [asSaved(bestMatch)] }));
  respond("POST /api/song-versions", songReply(bestMatch, lines, true));
  const user = userEvent.setup();
  render(<App />);

  await user.click(
    await screen.findByRole("button", { name: "Open 星の歌 by ミナト" }),
  );

  await screen.findByRole("table");
  expect(window.location.pathname).toBe("/song/101");
  expect(
    screen.getByText(/^Already translated · opened in \d+\.\d s$/),
  ).toBeTruthy();
});

// Spec 016 AC-9: Remove now calls DELETE …/saved; the song stays cached, so opening it again is
// instant (checked by the server test for spec 016 AC-5).
test("AC-4 and spec 016 AC-9: Remove asks first; confirming takes the song off, cancelling keeps it", async () => {
  respond(
    "GET /api/songs",
    jsonResponse(200, { songs: [asSaved(bestMatch), asSaved(liveMatch)] }),
  );
  respond("DELETE /api/songs/101/saved", jsonResponse(204, null));
  window.history.replaceState(null, "", "/library");
  const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false);
  const user = userEvent.setup();
  render(<App />);
  const remove = await screen.findByRole("button", { name: "Remove 星の歌" });

  await user.click(remove);
  expect(confirm).toHaveBeenCalledWith("Remove 星の歌 from your songs?");
  expect(screen.getByRole("button", { name: "Remove 星の歌" })).toBeTruthy();

  await user.click(remove);
  expect(screen.queryByRole("button", { name: "Remove 星の歌" })).toBeNull();
  expect(
    screen.getByRole("button", { name: "Remove 星の歌 (live)" }),
  ).toBeTruthy();
});

test("AC-6: a song address opens that song; Back returns to the library", async () => {
  window.history.replaceState(null, "", "/song/101");
  respond("POST /api/song-versions", songReply(bestMatch, lines, true));
  render(<App />);

  await screen.findByRole("table");
  expect(bodyOf("POST", "/api/song-versions")).toEqual({ id: 101 });

  await act(async () => {
    window.history.replaceState(null, "", "/library");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await Promise.resolve();
  });
  expect(screen.queryByRole("table")).toBeNull();
  expect(screen.getByText("Your songs will show up here.")).toBeTruthy();
});

test("AC-6: a song the server does not have shows home with the reason", async () => {
  window.history.replaceState(null, "", "/song/999");
  respond(
    "POST /api/song-versions",
    jsonResponse(404, {
      code: "song_not_found",
      message: "That song was not found.",
    }),
  );
  render(<App />);

  expect((await screen.findByRole("alert")).textContent).toContain(
    "That song was not found.",
  );
  expect(window.location.pathname).toBe("/");
  expect(screen.getByRole("heading", { name: HOME_TITLE })).toBeTruthy();
});

test("leaving a song and opening it again fetches it fresh and refreshes the tiles", async () => {
  const saved = () => jsonResponse(200, { songs: [asSaved(bestMatch)] });
  respond("GET /api/songs", saved(), saved(), saved(), saved(), saved());
  window.history.replaceState(null, "", "/library");
  respond(
    "POST /api/song-versions",
    songReply(bestMatch, lines, true),
    songReply(bestMatch, [{ ...firstLine, english: "Fresh road" }], true),
  );
  const user = userEvent.setup();
  render(<App />);
  const tile = { name: "Open 星の歌 by ミナト" };

  await user.click(await screen.findByRole("button", tile));
  await screen.findByRole("table");
  await user.click(screen.getByRole("button", { name: "Back to your songs" }));
  await user.click(await screen.findByRole("button", tile));

  expect(await screen.findByText("Fresh road")).toBeTruthy();
  const listCalls = fakeFetch.mock.calls.filter(
    ([input, init]) =>
      urlOf(input) === "/api/songs" && (init?.method ?? "GET") === "GET",
  );
  // On load, after each open, and on returning to the library.
  expect(listCalls.length).toBeGreaterThanOrEqual(4);
});

test("AC-6 and spec 021 AC-1: an unknown address shows home", async () => {
  window.history.replaceState(null, "", "/song/abc");
  render(<App />);

  expect(await screen.findByRole("heading", { name: HOME_TITLE })).toBeTruthy();
  expect(
    fakeFetch.mock.calls.some(
      ([input]) => urlOf(input) === "/api/song-versions",
    ),
  ).toBe(false);
});

test("AC-10: Focus hides the header and song header; Exit focus and leaving end it", async () => {
  respond("POST /api/song-search", jsonResponse(200, { results }));
  respond(
    "POST /api/song-versions",
    songReply(bestMatch),
    songReply(bestMatch),
  );
  const user = await findSong();
  await screen.findByRole("table");

  await user.click(screen.getByRole("button", { name: "Focus" }));
  expect(screen.queryByRole("search")).toBeNull();
  expect(screen.queryByRole("heading", { name: "星の歌" })).toBeNull();
  await user.click(screen.getByRole("button", { name: "Exit focus" }));
  expect(screen.getByRole("search")).toBeTruthy();

  await user.click(screen.getByRole("button", { name: "Focus" }));
  act(() => {
    navigate("/");
  });
  act(() => {
    navigate("/song/101");
  });
  expect(await screen.findByRole("button", { name: "Focus" })).toBeTruthy();
  expect(screen.getByRole("search")).toBeTruthy();
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

test("AC-5: while searching, the steps and the seconds show", async () => {
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
  const steps = within(screen.getByRole("list", { name: "Steps" }));
  expect(steps.getByText(/Finding the song/).textContent).toContain(
    "(in progress)",
  );
  expect(
    steps.getByText(/Getting the lyrics and translating/).textContent,
  ).toContain("(waiting)");
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
    "Already translated · opened in 0.0 s",
  );
});

test("removing a song clears its Saved mark in the search results", async () => {
  // On load, after the open, and on returning to the library.
  const saved = () => jsonResponse(200, { songs: [asSaved(liveMatch)] });
  respond("GET /api/songs", saved(), saved(), saved());
  respond("POST /api/song-search", jsonResponse(200, { results }));
  respond(
    "POST /api/song-versions",
    songReply(bestMatch),
    songReply(bestMatch),
  );
  respond("DELETE /api/songs/202/saved", jsonResponse(204, null));
  const user = await findSong();
  await screen.findByRole("table");

  await user.click(screen.getByRole("button", { name: "Back to your songs" }));
  await user.click(
    screen.getByRole("button", { name: "Remove 星の歌 (live)" }),
  );
  act(() => {
    navigate("/song/101");
  });

  await user.click(await screen.findByText("Not this one?"));
  expect(screen.queryByText("Saved")).toBeNull();
});
