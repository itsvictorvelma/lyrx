// Checks the theme button: it switches dark and light, remembers the choice, else follows the system.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ThemeButton } from "./ThemeButton";

function systemPrefersLight(light: boolean) {
  vi.stubGlobal(
    "matchMedia",
    (query: string) =>
      ({
        matches: light && query === "(prefers-color-scheme: light)",
      }) as MediaQueryList,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("AC-7: with nothing stored, the system setting decides and nothing is forced", () => {
  systemPrefersLight(true);
  render(<ThemeButton />);

  expect(
    screen.getByRole("button", { name: "Switch to dark mode" }),
  ).toBeTruthy();
  expect(document.documentElement.dataset.theme).toBeUndefined();
});

test("AC-7: the button switches the theme and the choice survives a reload", async () => {
  systemPrefersLight(false);
  const user = userEvent.setup();
  const { unmount } = render(<ThemeButton />);

  await user.click(
    screen.getByRole("button", { name: "Switch to light mode" }),
  );
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(window.localStorage.getItem("subbed-theme")).toBe("light");
  unmount();

  render(<ThemeButton />);
  expect(
    screen.getByRole("button", { name: "Switch to dark mode" }),
  ).toBeTruthy();
  expect(document.documentElement.dataset.theme).toBe("light");
});

test("AC-7: blocked storage falls back to the system setting", () => {
  systemPrefersLight(false);
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  render(<ThemeButton />);

  expect(
    screen.getByRole("button", { name: "Switch to light mode" }),
  ).toBeTruthy();
  vi.restoreAllMocks();
});
