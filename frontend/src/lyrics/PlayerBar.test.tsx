// Checks the song page with a fake YouTube player: links, the player bar, highlight, seek, sync, tabs.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App } from "../App";
import { BAD_LINK_MESSAGE } from "./PlayerBar";
import { NO_TIMINGS_TEXT } from "./SongPage";
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

// The fake player: its time is set by the test; seeks and play/pause are recorded.
let playerSeconds = 0;
let playerPlaying = false;
const seeks: number[] = [];
const createdFor: string[] = [];

class FakePlayer implements YouTubePlayerHandle {
  constructor(_element: HTMLElement, options: { videoId: string }) {
    createdFor.push(options.videoId);
  }
  getCurrentTime = () => playerSeconds;
  getDuration = () => 60;
  getPlayerState = () => (playerPlaying ? 1 : 2);
  playVideo = () => {
    playerPlaying = true;
  };
  pauseVideo = () => {
    playerPlaying = false;
  };
  seekTo = (seconds: number) => {
    seeks.push(seconds);
  };
  destroy = () => undefined;
}

const fakeFetch = vi.fn<typeof fetch>();

function songReply(
  lines: Line[],
  videoId: string | null = null,
  offsetMs = 0,
  saved = true,
) {
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
      saved,
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
        videoId: null,
        lastOpenedAt: Date.now(),
      };
      return Promise.resolve(
        new Response(JSON.stringify({ songs: [song] }), { status: 200 }),
      );
    }
    if (method === "POST" && url === "/api/song-versions") {
      return Promise.resolve(reply.clone());
    }
    if (method === "PUT" || method === "DELETE") {
      return Promise.resolve(new Response(null, { status: 204 }));
    }
    return Promise.reject(new TypeError(`no fake reply for ${method} ${url}`));
  });
}

// The calls to one address with one method, each with its parsed body.
function callsTo(method: string, url: string): unknown[] {
  return fakeFetch.mock.calls
    .filter(([input, init]) => input === url && init?.method === method)
    .map(([, init]): unknown =>
      typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
    );
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
    await screen.findByRole("button", { name: "Open 星の歌 by ミナト" }),
  );
  await screen.findByRole("table");
  return user;
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  playerSeconds = 0;
  playerPlaying = false;
  seeks.length = 0;
  createdFor.length = 0;
  fakeFetch.mockReset();
  vi.stubGlobal("fetch", fakeFetch);
  window.YT = { Player: FakePlayer };
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  // jsdom has no scrollTo; the calm-following test adds one.
  Reflect.deleteProperty(HTMLElement.prototype, "scrollTo");
  delete window.YT;
});

test("spec 012 AC-7: a YouTube link plays that video and is saved with the song", async () => {
  const user = await openSavedSong(songReply(LINES));
  await user.click(screen.getByRole("button", { name: "Add YouTube link" }));

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

test("spec 012 AC-7: any other link shows the error and embeds nothing", async () => {
  const user = await openSavedSong(songReply(LINES));
  await user.click(screen.getByRole("button", { name: "Add YouTube link" }));

  await user.type(
    screen.getByLabelText("YouTube link"),
    "https://vimeo.com/123",
  );
  await user.click(screen.getByRole("button", { name: "Play video" }));

  expect((await screen.findByRole("alert")).textContent).toBe(BAD_LINK_MESSAGE);
  expect(createdFor).toEqual([]);
  expect(putBodies()).toEqual([]);
});

test("spec 012 AC-8: the line being sung is highlighted, moved by the saved sync", async () => {
  playerSeconds = 5;
  await openSavedSong(songReply(LINES, VIDEO_ID, 500));

  await waitFor(() => {
    const current = document.querySelector('tr[aria-current="true"]');
    expect(current?.textContent).toContain("風が歌う");
  });
  expect(createdFor).toEqual([VIDEO_ID]);
  expect(screen.getByText("Sync: +0.50 s")).toBeTruthy();
});

test("spec 012 AC-9: clicking a line jumps the video to its start plus the sync", async () => {
  const user = await openSavedSong(songReply(LINES, VIDEO_ID, 500));
  await waitFor(() => {
    expect(createdFor).toEqual([VIDEO_ID]);
  });

  await user.click(screen.getByRole("button", { name: "Play from: 夜の月" }));

  expect(seeks).toEqual([9.5]);
});

test("spec 012 AC-10: Later and Earlier move the sync by a quarter second and save it", async () => {
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

test("spec 012 AC-11: a song without timings says so and has no sync or seek buttons", async () => {
  await openSavedSong(
    songReply(LINES.map((line) => ({ ...line, startMs: null }))),
  );

  expect(screen.getByText(NO_TIMINGS_TEXT)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Later" })).toBeNull();
  expect(screen.queryByRole("button", { name: /^Play from/ })).toBeNull();
});

test("AC-8: while the audio plays, the sung row is current", async () => {
  playerSeconds = 5;
  playerPlaying = true;
  await openSavedSong(songReply(LINES, VIDEO_ID));

  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "風が歌う",
    );
  });
});

test("spec 018 AC-2: a line is sung from 0.3 s before its start time, not earlier", async () => {
  // 風が歌う starts at 4.0 s; at 3.6 s the line before is still sung.
  playerSeconds = 3.6;
  await openSavedSong(songReply(LINES, VIDEO_ID));
  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "星の道",
    );
  });

  playerSeconds = 3.75;

  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "風が歌う",
    );
  });
});

test("spec 018 AC-3: the line after the sung one is marked next, across a verse gap", async () => {
  playerSeconds = 5;
  await openSavedSong(songReply(LINES, VIDEO_ID));

  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "風が歌う",
    );
  });
  const next = document.querySelectorAll("tr.next");
  expect(next).toHaveLength(1);
  expect(next[0]?.textContent).toContain("夜の月");
});

test("spec 018 AC-5: scrolling the lyrics pauses following; Back to the current line resumes it", async () => {
  // A laid-out view: 400px tall, with the sung row near its bottom, so following scrolls.
  const scrollTo = vi.fn();
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(400);
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(
    function (this: Element) {
      const top = this.matches("tr.current") ? 360 : 0;
      return { top, bottom: top + 40, height: 40 } as DOMRect;
    },
  );
  HTMLElement.prototype.scrollTo = scrollTo;
  playerSeconds = 5;
  playerPlaying = true;
  const user = await openSavedSong(songReply(LINES, VIDEO_ID));
  await waitFor(() => {
    expect(scrollTo).toHaveBeenCalled();
  });
  const lyrics = document.querySelector(".lyrics-scroll");
  if (lyrics === null) {
    throw new Error("no lyrics area");
  }

  // The page's own scrolling never pauses following.
  fireEvent.scroll(lyrics);
  expect(
    screen.queryByRole("button", { name: "Back to the current line" }),
  ).toBeNull();

  fireEvent.wheel(lyrics, { deltaY: 200 });
  const back = await screen.findByRole("button", {
    name: "Back to the current line",
  });
  scrollTo.mockClear();
  await user.click(back);

  expect(
    screen.queryByRole("button", { name: "Back to the current line" }),
  ).toBeNull();
  expect(scrollTo).toHaveBeenCalledWith({ top: 280, behavior: "smooth" });
  expect(document.activeElement).toBe(lyrics);
});

test("AC-9: play/pause, previous and next line, and the position slider control the audio", async () => {
  const user = await openSavedSong(songReply(LINES, VIDEO_ID, 500));
  await waitFor(() => {
    expect(createdFor).toEqual([VIDEO_ID]);
  });

  await user.click(screen.getByRole("button", { name: "Play" }));
  expect(playerPlaying).toBe(true);
  expect(screen.getByRole("button", { name: "Pause" })).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Pause" }));
  expect(playerPlaying).toBe(false);

  await user.click(screen.getByRole("button", { name: "Next line" }));
  fireEvent.change(screen.getByLabelText("Position"), {
    target: { value: "30000" },
  });
  expect(seeks).toEqual([1.5, 30]);

  playerSeconds = 9.6;
  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "夜の月",
    );
  });
  await user.click(screen.getByRole("button", { name: "Previous line" }));
  expect(seeks).toEqual([1.5, 30, 4.5]);
});

test("AC-9: with no audio chosen, the bar offers a YouTube link and a file", async () => {
  await openSavedSong(songReply(LINES));

  expect(screen.getByRole("button", { name: "Add YouTube link" })).toBeTruthy();
  expect(screen.getByLabelText("Play a file")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Play" })).toBeNull();
});

test("AC-11: the phone tabs pick the column shown next to the original", async () => {
  const user = await openSavedSong(songReply(LINES));
  const table = screen.getByRole("table");
  expect(table.dataset.phoneColumn).toBe("hiragana");

  await user.click(screen.getByRole("button", { name: "Romaji" }));
  expect(table.dataset.phoneColumn).toBe("romaji");
  await user.click(screen.getByRole("button", { name: "EN" }));
  expect(table.dataset.phoneColumn).toBe("english");
});

test("spec 012: saving the video of a song that is not saved is quiet, not an error", async () => {
  const user = await openSavedSong(songReply(LINES));
  const answerByAddress = fakeFetch.getMockImplementation();
  fakeFetch.mockImplementation((input, init) =>
    init?.method === "PUT"
      ? Promise.resolve(
          new Response(
            JSON.stringify({ code: "song_not_found", message: "Not saved." }),
            { status: 404 },
          ),
        )
      : (answerByAddress?.(input, init) ?? Promise.reject(new TypeError())),
  );
  await user.click(screen.getByRole("button", { name: "Add YouTube link" }));

  await user.type(
    screen.getByLabelText("YouTube link"),
    `https://youtu.be/${VIDEO_ID}`,
  );
  await user.click(screen.getByRole("button", { name: "Play video" }));

  await waitFor(() => {
    expect(putBodies()).toHaveLength(1);
  });
  expect(screen.queryByRole("alert")).toBeNull();
});

test("spec 016 AC-8: Save keeps the song with the video and sync now playing; Saved again unsaves it", async () => {
  const user = await openSavedSong(songReply(LINES, null, 0, false));
  await user.click(screen.getByRole("button", { name: "Add YouTube link" }));
  await user.type(
    screen.getByLabelText("YouTube link"),
    `https://youtu.be/${VIDEO_ID}`,
  );
  await user.click(screen.getByRole("button", { name: "Play video" }));
  await user.click(screen.getByRole("button", { name: "Later" }));
  const save = screen.getByRole("button", { name: "Save" });
  expect(save.getAttribute("aria-pressed")).toBe("false");

  await user.click(save);

  const saved = await screen.findByRole("button", { name: "Saved" });
  expect(saved.getAttribute("aria-pressed")).toBe("true");
  expect(callsTo("PUT", "/api/songs/101/saved")).toEqual([
    { videoId: VIDEO_ID, offsetMs: 250 },
  ]);

  await user.click(saved);

  const saveAgain = await screen.findByRole("button", { name: "Save" });
  expect(saveAgain.getAttribute("aria-pressed")).toBe("false");
  expect(callsTo("DELETE", "/api/songs/101/saved")).toHaveLength(1);
});

test("spec 016: a failed Save says so and keeps the button as it was", async () => {
  const user = await openSavedSong(songReply(LINES, null, 0, false));
  const answerByAddress = fakeFetch.getMockImplementation();
  fakeFetch.mockImplementation((input, init) =>
    init?.method === "PUT"
      ? Promise.resolve(
          new Response(
            JSON.stringify({ code: "internal_error", message: "Failed." }),
            { status: 500 },
          ),
        )
      : (answerByAddress?.(input, init) ?? Promise.reject(new TypeError())),
  );

  await user.click(screen.getByRole("button", { name: "Save" }));

  expect((await screen.findByRole("alert")).textContent).toContain(
    "Couldn't update your songs.",
  );
  expect(
    screen.getByRole("button", { name: "Save" }).getAttribute("aria-pressed"),
  ).toBe("false");
});
