// Checks the loading screen: the kana rain (decorative, stops cleanly, still, theme colours) and the terminal card.
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { readRainColors } from "./KanaRain";
import { SearchProgress } from "./SearchProgress";

// A stand-in for the 2D canvas (jsdom has none) that records what is drawn.
const drawn: string[] = [];
// The background colour of the last full-screen fill.
const filled: string[] = [];
const fakeContext = {
  font: "",
  fillStyle: "",
  globalAlpha: 1,
  shadowBlur: 0,
  shadowColor: "",
  fillRect() {
    filled.push(this.fillStyle);
  },
  setTransform: () => undefined,
  fillText: (text: string) => {
    drawn.push(text);
  },
};

// Animation frames are queued here and run by the test.
let frames = new Map<number, FrameRequestCallback>();
let nextFrame = 1;

function runFrames(now: number) {
  const due = frames;
  frames = new Map();
  due.forEach((callback) => {
    callback(now);
  });
}

function stubReducedMotion(reduce: boolean) {
  vi.stubGlobal(
    "matchMedia",
    (query: string) =>
      ({
        matches: reduce && query.includes("reduced-motion"),
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }) as unknown as MediaQueryList,
  );
}

beforeEach(() => {
  drawn.length = 0;
  filled.length = 0;
  frames = new Map();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
    fakeContext as unknown as CanvasRenderingContext2D,
  );
  // jsdom lays nothing out, so give the canvas a size.
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(400);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(300);
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    frames.set(nextFrame, callback);
    return nextFrame++;
  });
  vi.stubGlobal("cancelAnimationFrame", (id: number) => {
    frames.delete(id);
  });
  stubReducedMotion(false);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.documentElement.removeAttribute("style");
  delete document.documentElement.dataset.theme;
});

test("spec 017 AC-1: the loading screen shows the decorative rain and no placeholder rows", () => {
  const { container } = render(<SearchProgress stage="finding" />);

  const canvas = container.querySelector("canvas.kana-rain");
  expect(canvas?.getAttribute("aria-hidden")).toBe("true");
  expect(container.querySelector(".placeholder-row")).toBeNull();
  expect(container.querySelector(".progress-card .steps")).not.toBeNull();
});

test("spec 017 AC-2: the status line still says the step", () => {
  render(<SearchProgress stage="opening-found" />);

  expect(screen.getByRole("status").textContent).toContain(
    "Getting the lyrics and translating…",
  );
});

test("spec 017 AC-3: the rain falls while loading and asks for no frame once the page closes", () => {
  const { unmount } = render(<SearchProgress stage="finding" />);
  for (let step = 1; step <= 40; step += 1) {
    runFrames(step * 100);
  }
  expect(drawn.length).toBeGreaterThan(0);
  expect(frames.size).toBe(1);

  unmount();

  expect(frames.size).toBe(0);
});

test("spec 017 AC-4: under reduced motion the rain is drawn once and never animates", () => {
  stubReducedMotion(true);

  render(<SearchProgress stage="finding" />);

  expect(drawn.length).toBeGreaterThan(0);
  expect(frames.size).toBe(0);
});

test("spec 017 AC-5: the falling rain takes the new background when the theme changes", async () => {
  const root = document.documentElement;
  root.style.setProperty("--bg", "#0e0d12");
  render(<SearchProgress stage="finding" />);

  act(() => {
    root.style.setProperty("--bg", "#faf8fa");
    root.dataset.theme = "light";
  });

  await waitFor(() => {
    expect(filled.at(-1)).toBe("#faf8fa");
  });
});

test("spec 017 AC-5: the rain takes the theme's colours and redraws when the theme changes", async () => {
  stubReducedMotion(true);
  const root = document.documentElement;
  root.style.setProperty("--accent", "#ff7ab6");
  root.style.setProperty("--bg", "#0e0d12");
  expect(readRainColors()).toEqual({
    accent: "#ff7ab6",
    background: "#0e0d12",
  });
  render(<SearchProgress stage="finding" />);
  const drawnBefore = drawn.length;

  act(() => {
    root.style.setProperty("--accent", "#c92a74");
    root.dataset.theme = "light";
  });

  await waitFor(() => {
    expect(drawn.length).toBeGreaterThan(drawnBefore);
  });
  expect(fakeContext.fillStyle).toBe("#c92a74");
});

test("spec 017 AC-7: the terminal card shows text marks that screen readers skip, and a still spinner under reduced motion", () => {
  stubReducedMotion(true);
  vi.useFakeTimers();
  const { container } = render(<SearchProgress stage="opening-found" />);
  const marks = [...container.querySelectorAll(".step-mark")];
  const spinnerBefore = marks[1]?.textContent;

  act(() => {
    vi.advanceTimersByTime(1000);
  });

  expect(container.querySelector(".terminal-bar")?.textContent).toContain(
    "subbed@字幕",
  );
  expect(marks[0]?.textContent).toBe("[ OK ]");
  expect(marks[1]?.textContent).toBe(spinnerBefore);
  for (const decorative of container.querySelectorAll(
    ".step-mark, .prompt, .cursor, .terminal-bar",
  )) {
    expect(decorative.getAttribute("aria-hidden")).toBe("true");
  }
  expect(screen.getByText(/Finding the song/).textContent).toContain("(done)");
});

test("spec 017 AC-7: a waiting step is marked [ -- ]", () => {
  const { container } = render(<SearchProgress stage="finding" />);

  const marks = [...container.querySelectorAll(".step-mark")];

  expect(marks[1]?.textContent).toBe("[ -- ]");
});
