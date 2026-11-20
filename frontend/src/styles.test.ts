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

// The body of the first rule whose selector is exactly `selector` (outside media queries).
function ruleBody(selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?:^|\\n)${escaped} \\{([^}]*)\\}`).exec(css)?.[1] ?? "";
}

test("spec 018 AC-4: no dimmed rows, romaji bright and English quiet", () => {
  expect(css).not.toContain("is-playing");
  expect(ruleBody(".versions-table td.col-romaji")).toContain(
    "color: var(--text)",
  );
  expect(ruleBody(".versions-table .col-english")).toContain(
    "color: var(--dim)",
  );
});

test("spec 018 AC-6: tighter rows, narrower width, new sizes, and a verse divider", () => {
  const expected: [selector: string, declaration: string][] = [
    [".versions-table", "max-width: 72rem"],
    [".versions-table td", "--row-pad: 0.5rem"],
    [".versions-table td", "--line-box: 1.625rem"],
    [".versions-table .col-original", "width: 27%"],
    [".versions-table .col-hiragana", "width: 26%"],
    [".versions-table .col-romaji", "width: 25%"],
    [".versions-table .col-english", "width: 22%"],
    [".versions-table .col-original", "font-size: 1.25rem"],
    [".versions-table .col-hiragana", "font-size: 1.0625rem"],
    [".versions-table .col-romaji", "font-size: 1rem"],
    [".versions-table .col-english", "font-size: 0.9375rem"],
    [
      ".versions-table tbody + tbody tr:first-child td",
      "border-top: 1px solid var(--line)",
    ],
    [".is-focus .versions-table", "max-width: 81rem"],
    [".is-focus .versions-table td", "--row-pad: 0.75rem"],
    [".is-focus .versions-table td", "--line-box: 2.125rem"],
    [".is-focus .versions-table td.col-original", "font-size: 1.625rem"],
    [".is-focus .versions-table td.col-hiragana", "font-size: 1.3125rem"],
    [".is-focus .versions-table td.col-romaji", "font-size: 1.1875rem"],
    [".is-focus .versions-table td.col-english", "font-size: 1.0625rem"],
  ];
  for (const [selector, declaration] of expected) {
    expect(ruleBody(selector), selector).toContain(declaration);
  }
});

test("spec 026 AC-5: one line box for every column, baseline-aligned, with no --shift nudges", () => {
  const cell = ruleBody(".versions-table td");
  expect(cell).toContain("line-height: var(--line-box)");
  expect(cell).toContain("vertical-align: baseline");
  expect(css).not.toContain("--shift");
  expect(ruleBody(".versions-table .col-original")).not.toContain(
    "line-height",
  );
  expect(ruleBody(".seek-button")).toContain("display: inline-flex");
});

test("spec 026 AC-7: the sung row is lit pink with a glow, strongest on the original, and has no box", () => {
  const row = ruleBody(".versions-table tr.current td");
  expect(row).toContain("color: var(--accent)");
  expect(row).toContain("text-shadow: 0 0 10px var(--accent-glow)");
  expect(row).not.toContain("background");
  expect(ruleBody(".versions-table tr.current td.col-original")).toContain(
    "text-shadow: 0 0 18px var(--accent-glow)",
  );
  expect(css).not.toMatch(
    /tr\.current[^{]*\{[^}]*(background|box-shadow|border-radius)/,
  );
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
