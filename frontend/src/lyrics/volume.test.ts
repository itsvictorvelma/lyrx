// Checks the remembered volume (a broken value means full) and what Mute and Unmute change it to.
import { afterEach, expect, test } from "vitest";
import { storedVolume, storeVolume, toggledVolume } from "./volume";

afterEach(() => {
  window.localStorage.removeItem("lyrx-volume");
});

test("AC-3: a stored level is read back; a missing or broken one means 100", () => {
  expect(storedVolume()).toBe(100);
  storeVolume(35);
  expect(storedVolume()).toBe(35);
  for (const broken of ["", "loud", "-5", "101", "12.5"]) {
    window.localStorage.setItem("lyrx-volume", broken);
    expect(storedVolume()).toBe(100);
  }
});

test("AC-2: Mute goes to 0; Unmute brings back the level before, or 100", () => {
  expect(toggledVolume(60, 60)).toBe(0);
  expect(toggledVolume(0, 60)).toBe(60);
  expect(toggledVolume(0, 0)).toBe(100);
});
