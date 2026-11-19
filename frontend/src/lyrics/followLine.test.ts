// Checks the calm-following scroll decision: still until the sung row passes 60%, then land it at 20%.
import { expect, test } from "vitest";
import { scrollTarget } from "./followLine";

const VIEW_HEIGHT = 500;

test("spec 018 AC-1: a sung row in the top 60% of the view leaves the lyrics still", () => {
  expect(scrollTarget({ top: 100, bottom: 140 }, 0, VIEW_HEIGHT)).toBeNull();
  expect(scrollTarget({ top: 260, bottom: 300 }, 0, VIEW_HEIGHT)).toBeNull();
  expect(
    scrollTarget({ top: 1060, bottom: 1100 }, 1000, VIEW_HEIGHT),
  ).toBeNull();
});

test("spec 018 AC-1: a row past 60% scrolls so it lands 20% from the top", () => {
  expect(scrollTarget({ top: 280, bottom: 320 }, 0, VIEW_HEIGHT)).toBe(180);
});

test("spec 018 AC-1: a row above the view brings it back, never scrolling below 0", () => {
  expect(scrollTarget({ top: 600, bottom: 640 }, 900, VIEW_HEIGHT)).toBe(500);
  expect(scrollTarget({ top: 40, bottom: 80 }, 300, VIEW_HEIGHT)).toBe(0);
});
