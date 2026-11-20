// Checks the hero line: sung part by part, resting after three loops, still with reduced motion.
import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { HeroLine } from "./HeroLine";
import { HERO_ENGLISH, HERO_LAST_TICK, HERO_TICK_MS } from "./heroTiming";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function partStates(container: HTMLElement): (string | null)[] {
  return Array.from(container.querySelectorAll(".hero-part")).map((part) =>
    part.getAttribute("data-state"),
  );
}

function englishShown(container: HTMLElement): string | null {
  return (
    container.querySelector(".hero-english")?.getAttribute("data-shown") ?? null
  );
}

function advanceTicks(count: number) {
  for (let tick = 0; tick < count; tick += 1) {
    act(() => {
      vi.advanceTimersByTime(HERO_TICK_MS);
    });
  }
}

test("spec 021 AC-3: with reduced motion the whole line shows at once, labelled for screen readers", () => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query === "(prefers-reduced-motion: reduce)",
  }));
  const { container } = render(<HeroLine />);

  expect(partStates(container)).toEqual(["sung", "sung", "sung", "sung"]);
  expect(englishShown(container)).toBe("true");
  expect(
    screen.getByRole("img", {
      name: `Example line: 夜明けの街で君を待つ, ${HERO_ENGLISH}`,
    }),
  ).toBeTruthy();
});

test("spec 021 AC-4: the parts are sung one by one, and the line rests after three loops", () => {
  vi.useFakeTimers();
  const { container } = render(<HeroLine />);
  expect(partStates(container)).toEqual([
    "waiting",
    "waiting",
    "waiting",
    "waiting",
  ]);

  advanceTicks(1);
  expect(partStates(container)).toEqual([
    "current",
    "waiting",
    "waiting",
    "waiting",
  ]);
  advanceTicks(1);
  expect(partStates(container)).toEqual([
    "sung",
    "current",
    "waiting",
    "waiting",
  ]);
  expect(englishShown(container)).toBe("false");
  advanceTicks(3);
  expect(englishShown(container)).toBe("true");

  advanceTicks(HERO_LAST_TICK - 5);
  expect(partStates(container)).toEqual(["sung", "sung", "sung", "sung"]);
  expect(englishShown(container)).toBe("true");
  expect(vi.getTimerCount()).toBe(0);
});
