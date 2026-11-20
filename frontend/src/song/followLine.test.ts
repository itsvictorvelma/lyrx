// Checks steady following: the sung row's place 35% down the view, and the ease-out glide (spec 026).
import { renderHook } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import {
  GLIDE_MS,
  glidePosition,
  scrollTarget,
  useFollowLine,
} from "./followLine";

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

// A laid-out lyrics view: 400px tall, 2000px of lyrics, the sung row 360px down.
function laidOutView() {
  const view = document.createElement("div");
  view.innerHTML = '<p class="current"></p>';
  const row = view.querySelector("p");
  if (row === null) {
    throw new Error("no row");
  }
  Object.defineProperty(view, "clientHeight", { value: 400 });
  Object.defineProperty(view, "scrollHeight", { value: 2000 });
  vi.spyOn(view, "getBoundingClientRect").mockReturnValue({
    top: 0,
  } as DOMRect);
  vi.spyOn(row, "getBoundingClientRect").mockReturnValue({
    top: 360,
  } as DOMRect);
  const scrollTo = vi.fn();
  view.scrollTo = scrollTo;
  return { view, scrollTo };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("spec 026 AC-2: a new sung line cancels the glide still running and starts its own", () => {
  const { view } = laidOutView();
  const requestFrame = vi.fn().mockReturnValueOnce(11).mockReturnValueOnce(12);
  const cancelFrame = vi.fn();
  vi.stubGlobal("requestAnimationFrame", requestFrame);
  vi.stubGlobal("cancelAnimationFrame", cancelFrame);

  const { rerender } = renderHook(
    ({ line }) => {
      useFollowLine({ current: view }, line, true, ".current", "normal");
    },
    { initialProps: { line: 1 } },
  );
  expect(requestFrame).toHaveBeenCalledTimes(1);

  rerender({ line: 2 });

  expect(cancelFrame).toHaveBeenCalledWith(11);
  expect(requestFrame).toHaveBeenCalledTimes(2);
});

test("spec 026 AC-2: no glide starts while following is paused", () => {
  const { view, scrollTo } = laidOutView();
  const requestFrame = vi.fn();
  vi.stubGlobal("requestAnimationFrame", requestFrame);

  renderHook(() => {
    useFollowLine({ current: view }, 1, false, ".current", "normal");
  });

  expect(requestFrame).not.toHaveBeenCalled();
  expect(scrollTo).not.toHaveBeenCalled();
});

test("spec 026 AC-3: under reduced motion the view jumps straight to the target", () => {
  const { view, scrollTo } = laidOutView();
  const requestFrame = vi.fn();
  vi.stubGlobal("requestAnimationFrame", requestFrame);
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: true })),
  );

  renderHook(() => {
    useFollowLine({ current: view }, 1, true, ".current", "normal");
  });

  // 360 - 0.35 × 400 = 220.
  expect(scrollTo).toHaveBeenCalledExactlyOnceWith({
    top: 220,
    behavior: "instant",
  });
  expect(requestFrame).not.toHaveBeenCalled();
});
