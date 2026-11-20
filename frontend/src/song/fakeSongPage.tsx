// Test helpers for the song page: a fake YouTube player, a fake server (with accounts), and
// opening a song.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, vi } from "vitest";
import { App } from "../App";
import type { YouTubePlayerHandle } from "../player/YouTubePlayer";
import type { Line } from "../types";

export const VIDEO_ID = "abcDEF12_-z";
// Invented lines; the blank one is a verse gap.
export const LINES: Line[] = [
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

export function timed(
  index: number,
  original: string,
  startMs: number | null,
): Line {
  return {
    index,
    original,
    hiragana: "かな",
    romaji: "kana",
    english: `English ${String(index)}`,
    startMs,
  };
}

// The fake player: its time is set by the test; fakePlayer.seeks and play/pause are recorded.
export const fakePlayer = {
  seconds: 0,
  playing: false,
  seeks: [] as number[],
  createdFor: [] as string[],
  // The last volume set, and YouTube's "ready" call for the newest player.
  volume: null as number | null,
  rate: null as number | null,
  becomeReady: (() => undefined) as () => void,
};

export class FakePlayer implements YouTubePlayerHandle {
  constructor(
    _element: HTMLElement,
    options: { videoId: string; events: { onReady: () => void } },
  ) {
    fakePlayer.createdFor.push(options.videoId);
    fakePlayer.becomeReady = options.events.onReady;
  }
  getCurrentTime = () => fakePlayer.seconds;
  getDuration = () => 60;
  getPlayerState = () => (fakePlayer.playing ? 1 : 2);
  playVideo = () => {
    fakePlayer.playing = true;
  };
  pauseVideo = () => {
    fakePlayer.playing = false;
  };
  seekTo = (seconds: number) => {
    fakePlayer.seeks.push(seconds);
  };
  setVolume = (percent: number) => {
    fakePlayer.volume = percent;
  };
  setPlaybackRate = (rate: number) => {
    fakePlayer.rate = rate;
  };
  destroy = () => undefined;
}

export const fakeFetch = vi.fn<typeof fetch>();
// Who the fake server says is signed in; null makes the visitor a guest.
export const fakeAccount = { username: "mika" as string | null };
// The one password the fake server accepts.
export const FAKE_PASSWORD = "correct horse battery";

function json(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

// Sign in, create an account, sign out, and delete, as the server answers them.
function answerAccount(
  method: string,
  url: string,
  body: string,
): Promise<Response> | null {
  const sent = (body === "" ? {} : JSON.parse(body)) as Record<string, string>;
  if (url === "/api/account/sign-in" || url === "/api/account/sign-up") {
    if (sent.password !== FAKE_PASSWORD) {
      return json(
        {
          code: "sign_in_failed",
          message: "The username or password is not right.",
        },
        401,
      );
    }
    fakeAccount.username = (sent.username ?? "").toLowerCase();
    return json({ username: fakeAccount.username });
  }
  if (
    url === "/api/account/sign-out" ||
    (method === "DELETE" && url === "/api/account")
  ) {
    fakeAccount.username = null;
    return Promise.resolve(new Response(null, { status: 204 }));
  }
  return null;
}

export function songReply(
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

export function stubServer(reply: Response) {
  fakeFetch.mockImplementation((input, init) => {
    const method = init?.method ?? "GET";
    const url = typeof input === "string" ? input : "";
    const body = typeof init?.body === "string" ? init.body : "";
    const accountReply = answerAccount(method, url, body);
    if (accountReply !== null) {
      return accountReply;
    }
    if (method === "GET" && url === "/api/account") {
      return Promise.resolve(
        new Response(JSON.stringify({ username: fakeAccount.username }), {
          status: 200,
        }),
      );
    }
    if (method === "GET" && url === "/api/songs") {
      const song = {
        id: 101,
        track: "星の歌",
        artist: "ミナト",
        album: "",
        durationSeconds: 214,
        videoId: null,
        offsetMs: 0,
        lastOpenedAt: Date.now(),
      };
      return Promise.resolve(
        new Response(JSON.stringify({ songs: [song] }), { status: 200 }),
      );
    }
    if (method === "GET" && url === "/api/recent-songs") {
      return Promise.resolve(
        new Response(JSON.stringify({ songs: [] }), { status: 200 }),
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

// A guest opens the song at its address; nothing is saved for them.
export async function openSongAsGuest(reply: Response) {
  fakeAccount.username = null;
  stubServer(reply);
  window.history.replaceState(null, "", "/song/101");
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("table");
  return user;
}

export async function openSavedSong(reply: Response) {
  stubServer(reply);
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "Open 星の歌 by ミナト" }),
  );
  await screen.findByRole("table");
  return user;
}

// Every test file that opens a song calls this once at the top level.
export function installFakeSongPage() {
  beforeEach(() => {
    window.history.replaceState(null, "", "/library");
    fakePlayer.seconds = 0;
    fakePlayer.playing = false;
    fakePlayer.seeks.length = 0;
    fakePlayer.createdFor.length = 0;
    fakePlayer.volume = null;
    fakePlayer.rate = null;
    fakeAccount.username = "mika";
    window.localStorage.removeItem("lyrx-volume");
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
}
