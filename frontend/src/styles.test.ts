// Checks rules in styles.css that jsdom cannot compute, by reading the stylesheet as text.
import { expect, test } from "vitest";
import css from "./styles.css?raw";

const TEXT_PAIRS: [text: string, background: string][] = [
  ["--text", "--bg"],
  ["--text", "--surface"],
  ["--text", "--surface-2"],
  ["--dim", "--bg"],
  ["--dim", "--surface"],
  ["--dim", "--surface-2"],
  ["--accent", "--bg"],
  ["--accent", "--surface"],
  ["--accent-ink", "--accent"],
  ["--error", "--bg"],
  ["--error", "--surface"],
];

// The colour tokens (#rrggbb only) declared in the first block that opens with `opening`.
function tokens(opening: string): Map<string, string> {
  const start = css.indexOf(opening);
  if (start === -1) {
    throw new Error(`styles.css has no "${opening}" block`);
  }
  const block = css.slice(start, css.indexOf("}", start));
  const found = new Map<string, string>();
  for (const match of block.matchAll(/(--[a-z0-9-]+):\s*(#[0-9a-f]{6});/g)) {
    found.set(match[1] ?? "", match[2] ?? "");
  }
  return found;
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((at) => {
    const value = parseInt(hex.slice(at, at + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  const [red = 0, green = 0, blue = 0] = channels;
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(a: string, b: string): number {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((light ?? 0) + 0.05) / ((dark ?? 0) + 0.05);
}

const LIGHT = tokens(":root {");
const DARK = tokens(':root[data-theme="dark"] {');

test.each([
  ["light", LIGHT],
  ["dark", DARK],
])("AC-13: every text colour passes 4.5:1 in the %s theme", (_name, theme) => {
  for (const [text, background] of TEXT_PAIRS) {
    const ratio = contrast(theme.get(text) ?? "", theme.get(background) ?? "");
    expect(ratio, `${text} on ${background}`).toBeGreaterThanOrEqual(4.5);
  }
});

test("AC-13: the approved colours are the ones in the stylesheet", () => {
  expect(Object.fromEntries(LIGHT)).toMatchObject({
    "--bg": "#faf8fa",
    "--surface": "#ffffff",
    "--text": "#1b1820",
    "--dim": "#6a6575",
    "--accent": "#c92a74",
  });
  expect(Object.fromEntries(DARK)).toMatchObject({
    "--bg": "#0e0d12",
    "--surface": "#18161d",
    "--text": "#f3f0f5",
    "--dim": "#9c97a8",
    "--accent": "#ff7ab6",
  });
});

test("the system's dark tokens match the dark theme button's tokens", () => {
  expect(tokens(':root:not([data-theme="light"]) {')).toEqual(DARK);
});

test("AC-13: reduced motion turns off animation, transitions, and smooth scrolling", () => {
  const start = css.indexOf("@media (prefers-reduced-motion: reduce)");
  expect(start).toBeGreaterThan(-1);
  const block = css.slice(start);
  expect(block).toContain("animation: none !important");
  expect(block).toContain("transition: none !important");
  expect(block).toContain("scroll-behavior: auto !important");
});

test("dim rows use the dim colour, never transparency", () => {
  const rule =
    /\.versions-table\.is-playing tr:not\(\.current\) td \{([^}]*)\}/.exec(css);
  expect(rule?.[1]).toContain("color: var(--dim)");
  expect(rule?.[1]).not.toContain("opacity");
});

test("AC-11: below 720px only the chosen column shows next to the original", () => {
  const start = css.indexOf("@media (max-width: 719px)");
  expect(start).toBeGreaterThan(-1);
  const block = css.slice(start);
  for (const [shown, hidden] of [
    ["hiragana", ".col-romaji, .col-english"],
    ["romaji", ".col-hiragana, .col-english"],
    ["english", ".col-hiragana, .col-romaji"],
  ]) {
    expect(block).toContain(
      `.versions-table[data-phone-column="${shown ?? ""}"] :is(${hidden ?? ""})`,
    );
  }
});
