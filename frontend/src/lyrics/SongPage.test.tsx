// Checks the song page's study tools: hiding a column, looping a line, and keyboard shortcuts (spec 015).
import {
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";
import {
  fakePlayer,
  installFakeSongPage,
  LINES,
  openSavedSong,
  songReply,
  VIDEO_ID,
} from "./fakeSongPage";
import { SHORTCUT_LIST_TITLE } from "./ShortcutList";

installFakeSongPage();

beforeEach(() => {
  window.localStorage.clear();
});

function hideToggle(label: string): HTMLElement {
  const group = screen.getByRole("group", { name: "Hide columns" });
  return within(group).getByRole("button", { name: label });
}

// The romaji text shown in the table; every invented line's romaji is "kana".
function shownRomaji(): number {
  return within(screen.getByRole("table")).queryAllByText("kana").length;
}

function loopedRow(): string | undefined {
  return document.querySelector("tr.looped")?.textContent ?? undefined;
}

// Opens the song with the fake video at 5 s, where 風が歌う (4.0 s to 9.0 s) is sung.
async function openWhileSinging() {
  fakePlayer.seconds = 5;
  const user = await openSavedSong(songReply(LINES, VIDEO_ID));
  await waitFor(() => {
    expect(document.querySelector("tr.current")?.textContent).toContain(
      "風が歌う",
    );
  });
  return user;
}

test("AC-1: hiding Romaji covers every romaji cell and takes the text off the page; showing brings it back", async () => {
  const user = await openSavedSong(songReply(LINES));
  expect(shownRomaji()).toBe(3);

  await user.click(hideToggle("Romaji"));

  expect(hideToggle("Romaji").getAttribute("aria-pressed")).toBe("true");
  expect(shownRomaji()).toBe(0);
  expect(
    screen.getByRole("button", { name: "Show romaji for: 星の道" }),
  ).toBeTruthy();

  await user.click(hideToggle("Romaji"));
  expect(shownRomaji()).toBe(3);
});

test("AC-2: clicking one covered cell reveals only that cell", async () => {
  const user = await openSavedSong(songReply(LINES));
  await user.click(hideToggle("Romaji"));

  await user.click(
    screen.getByRole("button", { name: "Show romaji for: 風が歌う" }),
  );

  expect(shownRomaji()).toBe(1);
  expect(screen.getAllByRole("button", { name: /^Show romaji/ })).toHaveLength(
    2,
  );
});

test("AC-3: hidden columns are still hidden when the song is opened again", async () => {
  const user = await openSavedSong(songReply(LINES));
  await user.click(hideToggle("EN"));
  cleanup();
  window.history.replaceState(null, "", "/library");

  await openSavedSong(songReply(LINES));

  expect(hideToggle("EN").getAttribute("aria-pressed")).toBe("true");
  expect(screen.queryByText("English 0")).toBeNull();
});

test("AC-4: with Loop line on, playing past the line's end jumps back to its start", async () => {
  const user = await openWhileSinging();

  await user.click(screen.getByRole("button", { name: "Loop line" }));
  expect(loopedRow()).toContain("風が歌う");
  expect(screen.getByRole("img", { name: "Looping" })).toBeTruthy();

  fakePlayer.seconds = 9.1;
  await waitFor(() => {
    expect(fakePlayer.seeks).toContain(4);
  });
});

test("AC-5: Next line moves the loop; dragging the slider turns it off", async () => {
  const user = await openWhileSinging();
  await user.click(screen.getByRole("button", { name: "Loop line" }));

  await user.click(screen.getByRole("button", { name: "Next line" }));
  expect(fakePlayer.seeks).toEqual([9]);
  expect(loopedRow()).toContain("夜の月");

  fireEvent.change(screen.getByLabelText("Position"), {
    target: { value: "30000" },
  });
  expect(loopedRow()).toBeUndefined();
  expect(
    screen
      .getByRole("button", { name: "Loop line" })
      .getAttribute("aria-pressed"),
  ).toBe("false");
});

test("while looping, the lead-in to the next line does not move the sung line, so Next line goes one line on", async () => {
  const user = await openWhileSinging();
  await user.click(screen.getByRole("button", { name: "Loop line" }));

  // 8.8 s is in the 0.3 s lead-in to 夜の月 (9.0 s); the looped line stays the sung one.
  fakePlayer.seconds = 8.8;
  await waitFor(() => {
    expect(screen.getByText("0:08")).toBeTruthy();
  });
  expect(document.querySelector("tr.current")?.textContent).toContain(
    "風が歌う",
  );
  await user.click(screen.getByRole("button", { name: "Next line" }));

  expect(loopedRow()).toContain("夜の月");
});

test("AC-6: Loop line is disabled for a song without timings", async () => {
  await openSavedSong(
    songReply(
      LINES.map((line) => ({ ...line, startMs: null })),
      VIDEO_ID,
    ),
  );

  const loop = await screen.findByRole("button", { name: "Loop line" });
  expect((loop as HTMLButtonElement).disabled).toBe(true);
});

test("AC-7: each shortcut does what the list says", async () => {
  const user = await openWhileSinging();

  await user.keyboard(" ");
  expect(fakePlayer.playing).toBe(true);
  await user.keyboard("{ArrowRight}");
  await user.keyboard("{ArrowLeft}");
  expect(fakePlayer.seeks).toEqual([9, 1]);

  await user.keyboard("l");
  expect(loopedRow()).toContain("風が歌う");
  await user.keyboard("L");
  expect(loopedRow()).toBeUndefined();

  await user.keyboard("hre");
  for (const label of ["かな", "Romaji", "EN"]) {
    expect(hideToggle(label).getAttribute("aria-pressed")).toBe("true");
  }

  await user.keyboard("f");
  expect(screen.getByRole("button", { name: "Exit focus" })).toBeTruthy();
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: "Focus" })).toBeTruthy();

  await user.keyboard("?");
  expect(
    screen.getByRole("dialog", { name: SHORTCUT_LIST_TITLE }),
  ).toBeTruthy();
  await user.keyboard("?");
  expect(screen.queryByRole("dialog")).toBeNull();

  // Spec 021 AC-8: / jumps to the header's search box.
  await user.keyboard("/");
  expect(document.activeElement).toBe(
    screen.getByLabelText("Song name or artist"),
  );
});

test("AC-8: typing in the search box or the YouTube link field, or holding Ctrl, triggers nothing", async () => {
  const user = await openSavedSong(songReply(LINES));

  const pressed = (label: string) =>
    hideToggle(label).getAttribute("aria-pressed");

  await user.type(screen.getByLabelText("Song name or artist"), "fhre l");
  expect(screen.getByRole("search")).toBeTruthy();
  expect([pressed("かな"), pressed("Romaji"), pressed("EN")]).toEqual([
    "false",
    "false",
    "false",
  ]);

  await user.type(screen.getByLabelText("YouTube link"), "r");
  expect(pressed("Romaji")).toBe("false");

  (document.activeElement as HTMLElement).blur();
  await user.keyboard("{Control>}h{/Control}");
  expect(pressed("かな")).toBe("false");
});

test("AC-8: Space on a focused button presses only that button", async () => {
  const user = await openWhileSinging();

  screen.getByRole("button", { name: "Next line" }).focus();
  await user.keyboard(" ");

  expect(fakePlayer.seeks).toEqual([9]);
  expect(fakePlayer.playing).toBe(false);
});

test("AC-9: the shortcut list opens from its button, takes focus, and Esc gives focus back", async () => {
  const user = await openSavedSong(songReply(LINES));
  const opener = screen.getByRole("button", { name: "Keyboard shortcuts" });

  await user.click(opener);

  const dialog = screen.getByRole("dialog", { name: SHORTCUT_LIST_TITLE });
  expect(dialog.contains(document.activeElement)).toBe(true);
  expect(within(dialog).getByText("Loop line on or off")).toBeTruthy();

  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(opener);
});

test("spec 014 AC-19: the song page credits LRCLIB with a link", async () => {
  await openSavedSong(songReply(LINES));

  const link = screen.getByRole("link", { name: "LRCLIB" });
  expect(link.closest("p")?.textContent).toBe("Lyrics from LRCLIB");
  expect(link.getAttribute("href")).toBe("https://lrclib.net");
  expect(link.getAttribute("rel")).toBe("noopener noreferrer");
});
