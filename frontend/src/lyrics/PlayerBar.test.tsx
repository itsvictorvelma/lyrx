// Checks the song page with a fake YouTube player: links, the player bar, highlight, seek, sync, tabs.
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import {
  fakeFetch,
  fakePlayer,
  installFakeSongPage,
  LINES,
  openSavedSong,
  songReply,
  VIDEO_ID,
} from "./fakeSongPage";
import { BAD_LINK_MESSAGE, PLAY_ALONG_HINT } from "./PlayerBar";
import { NO_TIMINGS_TEXT } from "./SongPage";

installFakeSongPage();

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

test("spec 012 AC-7: a YouTube link plays that video and is saved with the song", async () => {
  const user = await openSavedSong(songReply(LINES));
  await user.click(screen.getByRole("button", { name: "Add YouTube link" }));

  await user.type(
    screen.getByLabelText("YouTube link"),
    `https://youtu.be/${VIDEO_ID}`,
  );
  await user.click(screen.getByRole("button", { name: "Play video" }));

  await waitFor(() => {
    expect(fakePlayer.createdFor).toEqual([VIDEO_ID]);
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
  expect(fakePlayer.createdFor).toEqual([]);
  expect(putBodies()).toEqual([]);
});

test("spec 012 AC-8: the line being sung is highlighted, moved by the saved sync", async () => {
  fakePlayer.seconds = 5;
  await openSavedSong(songReply(LINES, VIDEO_ID, 500));

  await waitFor(() => {
    const current = document.querySelector('tr[aria-current="true"]');
    expect(current?.textContent).toContain("風が歌う");
  });
  expect(fakePlayer.createdFor).toEqual([VIDEO_ID]);
  expect(screen.getByText("Sync: +0.50 s")).toBeTruthy();
});

test("spec 012 AC-9: clicking a line jumps the video to its start plus the sync", async () => {
  const user = await openSavedSong(songReply(LINES, VIDEO_ID, 500));
  await waitFor(() => {
    expect(fakePlayer.createdFor).toEqual([VIDEO_ID]);
  });

  await user.click(screen.getByRole("button", { name: "Play from: 夜の月" }));

  expect(fakePlayer.seeks).toEqual([9.5]);
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
  fakePlayer.seconds = 5;
  fakePlayer.playing = true;
  await openSavedSong(songReply(LINES, VIDEO_ID));

  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "風が歌う",
    );
  });
});

test("spec 018 AC-2: a line is sung from 0.3 s before its start time, not earlier", async () => {
  // 風が歌う starts at 4.0 s; at 3.6 s the line before is still sung.
  fakePlayer.seconds = 3.6;
  await openSavedSong(songReply(LINES, VIDEO_ID));
  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "星の道",
    );
  });

  fakePlayer.seconds = 3.75;

  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "風が歌う",
    );
  });
});

test("spec 018 AC-3: the line after the sung one is marked next, across a verse gap", async () => {
  fakePlayer.seconds = 5;
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
  fakePlayer.seconds = 5;
  fakePlayer.playing = true;
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
    expect(fakePlayer.createdFor).toEqual([VIDEO_ID]);
  });

  await user.click(screen.getByRole("button", { name: "Play" }));
  expect(fakePlayer.playing).toBe(true);
  expect(screen.getByRole("button", { name: "Pause" })).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Pause" }));
  expect(fakePlayer.playing).toBe(false);

  await user.click(screen.getByRole("button", { name: "Next line" }));
  fireEvent.change(screen.getByLabelText("Position"), {
    target: { value: "30000" },
  });
  expect(fakePlayer.seeks).toEqual([1.5, 30]);

  fakePlayer.seconds = 9.6;
  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "夜の月",
    );
  });
  await user.click(screen.getByRole("button", { name: "Previous line" }));
  expect(fakePlayer.seeks).toEqual([1.5, 30, 4.5]);
});

test("spec 022 AC-1, AC-4: the volume slider sets the YouTube player's volume, also once it is ready", async () => {
  window.localStorage.setItem("lyrx-volume", "70");
  await openSavedSong(songReply(LINES, VIDEO_ID));
  await waitFor(() => {
    expect(fakePlayer.createdFor).toEqual([VIDEO_ID]);
  });
  expect(fakePlayer.volume).toBe(70);

  fireEvent.change(screen.getByLabelText("Volume"), {
    target: { value: "40" },
  });
  expect(fakePlayer.volume).toBe(40);
  expect(screen.getByLabelText("Volume").getAttribute("aria-valuetext")).toBe(
    "40%",
  );

  // YouTube's player only takes a volume once ready: the level is applied again then.
  fakePlayer.volume = null;
  fakePlayer.becomeReady();
  expect(fakePlayer.volume).toBe(40);
});

test("spec 022 AC-2, AC-3: Mute and Unmute, and the level is remembered", async () => {
  const user = await openSavedSong(songReply(LINES, VIDEO_ID));
  await waitFor(() => {
    expect(fakePlayer.createdFor).toEqual([VIDEO_ID]);
  });
  fireEvent.change(screen.getByLabelText("Volume"), {
    target: { value: "55" },
  });

  await user.click(screen.getByRole("button", { name: "Mute" }));
  expect(fakePlayer.volume).toBe(0);
  expect(window.localStorage.getItem("lyrx-volume")).toBe("0");
  await user.click(screen.getByRole("button", { name: "Unmute" }));
  expect(fakePlayer.volume).toBe(55);
  expect(window.localStorage.getItem("lyrx-volume")).toBe("55");

  // Moving the slider up from 0 also unmutes.
  await user.click(screen.getByRole("button", { name: "Mute" }));
  fireEvent.change(screen.getByLabelText("Volume"), {
    target: { value: "20" },
  });
  expect(fakePlayer.volume).toBe(20);
  expect(screen.getByRole("button", { name: "Mute" })).toBeTruthy();
});

test("spec 022 AC-1, AC-3: an audio file starts at the current level and follows the slider", async () => {
  // jsdom has no object URLs; a URL class with them stands in for this test.
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = () => "blob:fake";
      static revokeObjectURL = () => undefined;
    },
  );
  window.localStorage.setItem("lyrx-volume", "30");
  const user = await openSavedSong(songReply(LINES));

  await user.upload(
    screen.getByLabelText("Play a file"),
    new File(["fake"], "song.mp3", { type: "audio/mpeg" }),
  );
  const audio = document.querySelector("audio");
  expect(audio?.volume).toBeCloseTo(0.3);

  fireEvent.change(screen.getByLabelText("Volume"), {
    target: { value: "80" },
  });
  expect(audio?.volume).toBeCloseTo(0.8);
});

test("spec 024 AC-1: the speed button cycles and sets the YouTube player's rate, also once ready", async () => {
  const user = await openSavedSong(songReply(LINES, VIDEO_ID));
  await waitFor(() => {
    expect(fakePlayer.createdFor).toEqual([VIDEO_ID]);
  });
  expect(fakePlayer.rate).toBe(1);

  await user.click(screen.getByRole("button", { name: "Playback speed: 1×" }));
  expect(fakePlayer.rate).toBe(0.75);
  await user.click(
    screen.getByRole("button", { name: "Playback speed: 0.75×" }),
  );
  expect(fakePlayer.rate).toBe(0.5);

  fakePlayer.rate = null;
  fakePlayer.becomeReady();
  expect(fakePlayer.rate).toBe(0.5);

  await user.click(
    screen.getByRole("button", { name: "Playback speed: 0.5×" }),
  );
  expect(fakePlayer.rate).toBe(1);
});

test("spec 024 AC-2, AC-4: an audio file follows the speed button; the hint goes once audio plays", async () => {
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = () => "blob:fake";
      static revokeObjectURL = () => undefined;
    },
  );
  const user = await openSavedSong(songReply(LINES));
  expect(screen.getByText(PLAY_ALONG_HINT)).toBeTruthy();

  await user.upload(
    screen.getByLabelText("Play a file"),
    new File(["fake"], "song.mp3", { type: "audio/mpeg" }),
  );
  expect(screen.queryByText(PLAY_ALONG_HINT)).toBeNull();

  await user.click(screen.getByRole("button", { name: "Playback speed: 1×" }));
  expect(document.querySelector("audio")?.playbackRate).toBe(0.75);
});

test("spec 024: a new player for the same song keeps the chosen speed", async () => {
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = () => "blob:fake";
      static revokeObjectURL = () => undefined;
    },
  );
  const user = await openSavedSong(songReply(LINES, VIDEO_ID));
  await user.click(screen.getByRole("button", { name: "Playback speed: 1×" }));

  await user.click(screen.getByRole("button", { name: "Change audio" }));
  await user.upload(
    screen.getByLabelText("Play a file"),
    new File(["fake"], "song.mp3", { type: "audio/mpeg" }),
  );
  expect(document.querySelector("audio")?.playbackRate).toBe(0.75);
});

test("spec 024 AC-3: Find on YouTube opens a search for the song in a new tab", async () => {
  await openSavedSong(songReply(LINES));

  const link = screen.getByRole("link", { name: "Find on YouTube" });
  expect(link.getAttribute("href")).toBe(
    "https://www.youtube.com/results?search_query=" +
      encodeURIComponent("星の歌 ミナト"),
  );
  expect(link.getAttribute("target")).toBe("_blank");
  expect(link.getAttribute("rel")).toBe("noopener noreferrer");
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

  const tabs = within(screen.getByRole("group", { name: "Second column" }));
  await user.click(tabs.getByRole("button", { name: "Romaji" }));
  expect(table.dataset.phoneColumn).toBe("romaji");
  await user.click(tabs.getByRole("button", { name: "EN" }));
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
