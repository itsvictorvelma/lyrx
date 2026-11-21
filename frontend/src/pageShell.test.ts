// Checks index.html: the link preview tags and icons, and that the files they point to exist.
import { expect, test } from "vitest";
import html from "../index.html?raw";
import touchIcon from "../public/apple-touch-icon.png?url";
import favicon from "../public/favicon.svg?url";
import previewImage from "../public/og-image.png?url";

test("spec 025 AC-2: the page has the preview tags and icon links, and the files exist", () => {
  // Prettier may wrap a tag over lines; compare with the whitespace collapsed.
  const page = html.replace(/\s+/g, " ");
  for (const tag of [
    '<meta name="description"',
    '<meta property="og:title" content="Subbed"',
    '<meta property="og:description"',
    '<meta property="og:image" content="/og-image.png"',
    '<meta name="twitter:card" content="summary_large_image"',
    '<link rel="icon" href="/favicon.svg"',
    '<link rel="apple-touch-icon" href="/apple-touch-icon.png"',
  ]) {
    expect(page).toContain(tag);
  }
  // A missing file fails the import above; these only confirm each resolved.
  expect([previewImage, favicon, touchIcon].every(Boolean)).toBe(true);
});
