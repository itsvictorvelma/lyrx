// Checks steady following: the sung row's place 35% down the view, and the ease-out glide (spec 026).
import { expect, test } from "vitest";
import { GLIDE_MS, glidePosition, scrollTarget } from "./followLine";

const VIEW_HEIGHT = 500;
const MAX_SCROLL = 3000;

test("spec 026 AC-1: the sung row is placed 35% down the view", () => {
  expect(scrollTarget(1000, VIEW_HEIGHT, MAX_SCROLL)).toBe(825);
  expect(scrollTarget(400, VIEW_HEIGHT, MAX_SCROLL)).toBe(225);
});

test("spec 026 AC-1: the target stays within what can be scrolled", () => {
  expect(scrollTarget(100, VIEW_HEIGHT, MAX_SCROLL)).toBe(0);
  expect(scrollTarget(3400, VIEW_HEIGHT, MAX_SCROLL)).toBe(MAX_SCROLL);
  // A song shorter than the view never scrolls.
  expect(scrollTarget(400, VIEW_HEIGHT, -120)).toBe(0);
});

test("spec 026 AC-3: a glide eases out over 0.45 s and then stays at its target", () => {
  expect(GLIDE_MS).toBe(450);
  expect(glidePosition(0, 300, 0)).toBe(0);
  // Ease-out: well past halfway at half the time.
  expect(glidePosition(0, 300, GLIDE_MS / 2)).toBeCloseTo(262.5);
  expect(glidePosition(0, 300, GLIDE_MS)).toBe(300);
  expect(glidePosition(0, 300, GLIDE_MS * 3)).toBe(300);
  expect(glidePosition(500, 200, GLIDE_MS)).toBe(200);
});
