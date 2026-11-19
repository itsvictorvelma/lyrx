// Checks which key presses become shortcuts and which are left to the page.
import { expect, test } from "vitest";
import { shortcutFor } from "./shortcuts";

function press(
  key: string,
  target: Element = document.body,
  modifiers: KeyboardEventInit = {},
): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { key, ...modifiers });
  Object.defineProperty(event, "target", { value: target });
  return event;
}

test("each key in the list maps to its shortcut, upper or lower case", () => {
  expect(shortcutFor(press(" "))).toEqual({ kind: "togglePlay" });
  expect(shortcutFor(press("ArrowLeft"))).toEqual({ kind: "previousLine" });
  expect(shortcutFor(press("ArrowRight"))).toEqual({ kind: "nextLine" });
  expect(shortcutFor(press("L"))).toEqual({ kind: "toggleLoop" });
  expect(shortcutFor(press("r"))).toEqual({
    kind: "toggleColumn",
    column: "romaji",
  });
  expect(shortcutFor(press("?"))).toEqual({ kind: "toggleShortcutList" });
  expect(shortcutFor(press("x"))).toBeNull();
});

test("AC-8: keys typed into a field, or held with Ctrl, Cmd, or Alt, are left alone", () => {
  for (const tag of ["input", "textarea", "select"]) {
    expect(shortcutFor(press("h", document.createElement(tag)))).toBeNull();
  }
  expect(shortcutFor(press("h", document.body, { ctrlKey: true }))).toBeNull();
  expect(shortcutFor(press("h", document.body, { metaKey: true }))).toBeNull();
  expect(shortcutFor(press("h", document.body, { altKey: true }))).toBeNull();
});

test("a held key fires its shortcut once, not again on each repeat", () => {
  expect(shortcutFor(press("h", document.body, { repeat: true }))).toBeNull();
});

test("AC-8: Space on a button or link is left to it; other keys still work there", () => {
  const button = document.createElement("button");
  expect(shortcutFor(press(" ", button))).toBeNull();
  expect(shortcutFor(press(" ", document.createElement("a")))).toBeNull();
  expect(shortcutFor(press("l", button))).toEqual({ kind: "toggleLoop" });
});
