// Checks rules in styles.css that jsdom cannot compute, by reading the stylesheet as text.
import { expect, test } from "vitest";
import css from "./styles.css?raw";

function ruleBody(selector: string): string {
  const match = new RegExp(`(?:^|\\n)${selector}\\s*\\{([^}]*)\\}`).exec(css);
  if (match === null) {
    throw new Error(`styles.css has no "${selector}" rule`);
  }
  return match[1] ?? "";
}

test("test_ac34_paste_box_border_uses_the_muted_color", () => {
  const border = /(?:^|;|\s)border\s*:\s*([^;]*);/.exec(ruleBody("textarea"));

  expect(border?.[1]).toContain("var(--color-muted)");
});
