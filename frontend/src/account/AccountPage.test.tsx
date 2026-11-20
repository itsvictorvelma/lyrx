// Checks signing in from Save and back to the song, sign-in errors, sign out, and delete (spec 014).
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";
import { App } from "../App";
import {
  FAKE_PASSWORD,
  fakeAccount,
  fakeFetch,
  installFakeSongPage,
  LINES,
  openSongAsGuest,
  songReply,
  stubServer,
} from "../lyrics/fakeSongPage";

installFakeSongPage();

function mainNav() {
  return within(screen.getByRole("navigation", { name: "Main" }));
}

async function signIn(
  user: ReturnType<typeof userEvent.setup>,
  password = FAKE_PASSWORD,
) {
  await user.type(await screen.findByLabelText("Username"), "Mika");
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(
    within(screen.getByRole("form", { name: "Sign in" })).getByRole("button", {
      name: "Sign in",
    }),
  );
}

test("AC-15: Save sends a guest to sign in, then back to the song, with their name and songs", async () => {
  const user = await openSongAsGuest(songReply(LINES, null, 0, false));
  expect(mainNav().getByRole("link", { name: "Sign in" })).toBeTruthy();
  const entries = window.history.length;

  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(window.location.pathname).toBe("/account");
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  expect(document.title).toBe("Sign in · Lyrx");

  await signIn(user);

  await screen.findByRole("table");
  expect(window.location.pathname).toBe("/song/101");
  // /account was replaced, so Back on the song skips the sign-in page.
  expect(window.history.length).toBe(entries + 1);
  expect(mainNav().getByRole("link", { name: "mika" })).toBeTruthy();

  await user.click(mainNav().getByRole("link", { name: "Your songs" }));
  expect(
    await screen.findByRole("button", { name: "Open 星の歌 by ミナト" }),
  ).toBeTruthy();
});

test("AC-15: a sign-in error shows as text and keeps the guest on the page", async () => {
  const user = await openSongAsGuest(songReply(LINES, null, 0, false));
  await user.click(mainNav().getByRole("link", { name: "Sign in" }));

  await signIn(user, "wrong password");

  expect((await screen.findByRole("alert")).textContent).toBe(
    "The username or password is not right.",
  );
  expect(window.location.pathname).toBe("/account");
  expect(fakeAccount.username).toBeNull();
});

test("AC-16: Sign out on /account returns to the guest home", async () => {
  window.history.replaceState(null, "", "/account");
  stubServer(songReply(LINES));
  const user = userEvent.setup();
  render(<App />);

  expect((await screen.findByText(/Signed in as/)).textContent).toBe(
    "Signed in as mika",
  );
  expect(document.title).toBe("Your account · Lyrx");
  await user.click(screen.getByRole("button", { name: "Sign out" }));

  expect(window.location.pathname).toBe("/");
  expect(
    await screen.findByText("to save songs.", { exact: false }),
  ).toBeTruthy();
  expect(mainNav().getByRole("link", { name: "Sign in" })).toBeTruthy();
});

test("AC-16: Delete account asks for the password, then returns to the guest home", async () => {
  window.history.replaceState(null, "", "/account");
  stubServer(songReply(LINES));
  const user = userEvent.setup();
  render(<App />);

  await user.click(
    await screen.findByRole("button", { name: "Delete account" }),
  );
  await user.type(screen.getByLabelText("Password"), FAKE_PASSWORD);
  await user.click(screen.getByRole("button", { name: "Delete my account" }));

  const deleteCall = fakeFetch.mock.calls.find(
    ([url, init]) => url === "/api/account" && init?.method === "DELETE",
  );
  expect(deleteCall?.[1]?.body).toBe(
    JSON.stringify({ password: FAKE_PASSWORD }),
  );
  expect(window.location.pathname).toBe("/");
  expect(mainNav().getByRole("link", { name: "Sign in" })).toBeTruthy();
});
