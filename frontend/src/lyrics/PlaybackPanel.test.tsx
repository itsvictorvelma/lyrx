// Checks playing along on the whole page, with a fake YouTube player: links, highlight, seek, sync.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "../App";
import { BAD_LINK_MESSAGE, NO_TIMINGS_TEXT } from "./PlaybackPanel";
import type { YouTubePlayerHandle } from "./YouTubePlayer";
import type { Line } from "./types";

const VIDEO_ID = "abcDEF12_-z";
// Invented lines; the blank one is a verse gap.
const LINES: Line[] = [
  timed(0, "星の道", 1000),
  timed(1, "風が歌う", 4000),
  {
    index: 2,
    original: "",
    hiragana: "",
    romaji: "",
    english: "",
    startMs: null,
  },
  timed(3, "夜の月", 9000),
];

function timed(index: number, original: string, startMs: number | null): Line {
  return {
    index,
    original,
    hiragana: "かな",
    romaji: "kana",
    english: `English ${String(index)}`,
    startMs,
  };
}

// The fake player: its time is set by the test, and its seeks are recorded.
let playerSeconds = 0;
const seeks: number[] = [];
const createdFor: string[] = [];

class FakePlayer implements YouTubePlayerHandle {
  constructor(_element: HTMLElement, options: { videoId: string }) {
    createdFor.push(options.videoId);
  }
  getCurrentTime = () => playerSeconds;
  seekTo = (seconds: number) => {
    seeks.push(seconds);
  };
  destroy = () => undefined;
}

const fakeFetch = vi.fn<typeof fetch>();

function songReply(lines: Line[], videoId: string | null = null, offsetMs = 0) {
  const song = {
    id: 101,
    track: "星の歌",
    artist: "ミナト",
    album: "",
    durationSeconds: 214,
  };
  return new Response(
    JSON.stringify({
      song,
      lines,
      fromLibrary: true,
      playback: { videoId, offsetMs },
    }),
    { status: 200 },
  );
}

function stubServer(reply: Response) {
  fakeFetch.mockImplementation((input, init) => {
    const method = init?.method ?? "GET";
    const url = typeof input === "string" ? input : "";
    if (method === "GET" && url === "/api/songs") {
      const song = {
        id: 101,
        track: "星の歌",
        artist: "ミナト",
        album: "",
        durationSeconds: 214,
      };
      return Promise.resolve(
        new Response(JSON.stringify({ songs: [song] }), { status: 200 }),
      );
    }
    if (method === "POST" && url === "/api/song-versions") {
      return Promise.resolve(reply.clone());
    }
    if (method === "PUT") {
      return Promise.resolve(new Response(null, { status: 204 }));
    }
    return Promise.reject(new TypeError(`no fake reply for ${method} ${url}`));
  });
}

function putBodies(): unknown[] {
  return fakeFetch.mock.calls
    .filter(([, init]) => init?.method === "PUT")
    .map(([, init]): unknown =>
      typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
    );
}

async function openSavedSong(reply: Response) {
  stubServer(reply);
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "星の歌 — ミナト, 3:34" }),
  );
  await screen.findByRole("table");
  return user;
}

beforeEach(() => {
  playerSeconds = 0;
  seeks.length = 0;
  createdFor.length = 0;
  fakeFetch.mockReset();
  vi.stubGlobal("fetch", fakeFetch);
  window.YT = { Player: FakePlayer };
});

afterEach(() => {
  vi.unstubAllGlobals();
  delete window.YT;
});

test("AC-7: a YouTube link plays that video and is saved with the song", async () => {
  const user = await openSavedSong(songReply(LINES));

  await user.type(
    screen.getByLabelText("YouTube link"),
    `https://youtu.be/${VIDEO_ID}`,
  );
  await user.click(screen.getByRole("button", { name: "Play video" }));

  await waitFor(() => {
    expect(createdFor).toEqual([VIDEO_ID]);
  });
  expect(putBodies()).toEqual([{ videoId: VIDEO_ID, offsetMs: 0 }]);
});

test("AC-7: any other link shows the error and embeds nothing", async () => {
  const user = await openSavedSong(songReply(LINES));

  await user.type(
    screen.getByLabelText("YouTube link"),
    "https://vimeo.com/123",
  );
  await user.click(screen.getByRole("button", { name: "Play video" }));

  expect((await screen.findByRole("alert")).textContent).toBe(BAD_LINK_MESSAGE);
  expect(createdFor).toEqual([]);
  expect(putBodies()).toEqual([]);
});

test("AC-8: the line being sung is highlighted, moved by the saved sync", async () => {
  playerSeconds = 5;
  await openSavedSong(songReply(LINES, VIDEO_ID, 500));

  await waitFor(() => {
    const current = document.querySelector('tr[aria-current="true"]');
    expect(current?.textContent).toContain("風が歌う");
  });
  expect(createdFor).toEqual([VIDEO_ID]);
  expect(screen.getByText("Sync: +0.50 s")).toBeTruthy();
});

test("AC-9: clicking a line jumps the video to its start plus the sync", async () => {
  const user = await openSavedSong(songReply(LINES, VIDEO_ID, 500));
  await waitFor(() => {
    expect(createdFor).toEqual([VIDEO_ID]);
  });

  await user.click(screen.getByRole("button", { name: "Play from: 夜の月" }));

  expect(seeks).toEqual([9.5]);
});

test("AC-10: Later and Earlier move the sync by a quarter second and save it", async () => {
  const user = await openSavedSong(songReply(LINES, VIDEO_ID));

  await user.click(screen.getByRole("button", { name: "Later" }));
  await user.click(screen.getByRole("button", { name: "Later" }));
  await user.click(screen.getByRole("button", { name: "Earlier" }));

  expect(screen.getByText("Sync: +0.25 s")).toBeTruthy();
  expect(putBodies()).toEqual([
    { videoId: VIDEO_ID, offsetMs: 250 },
    { videoId: VIDEO_ID, offsetMs: 500 },
    { videoId: VIDEO_ID, offsetMs: 250 },
  ]);
});

test("AC-11: a song without timings says so and has no sync or seek buttons", async () => {
  await openSavedSong(
    songReply(LINES.map((line) => ({ ...line, startMs: null }))),
  );

  expect(screen.getByText(NO_TIMINGS_TEXT)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Later" })).toBeNull();
  expect(screen.queryByRole("button", { name: /^Play from/ })).toBeNull();
});
