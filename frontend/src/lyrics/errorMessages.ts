// Turns a server error code into the message the page shows (spec 001, the page).
import type { PageErrorCode } from "./types";

export const FALLBACK_MESSAGE = "Something went wrong. Try again.";

export const SERVER_UNREACHABLE_MESSAGE =
  "Could not reach the Lyrx server. Is it running?";

// A Map, not an object, so names like "toString" or "__proto__" are never found.
const MESSAGES_BY_CODE = new Map<PageErrorCode, string>([
  ["empty_input", "Paste some lyrics first."],
  ["no_japanese", "No Japanese text found. Paste Japanese lyrics."],
  [
    "input_too_large",
    "The lyrics are too long. The limit is 5,000 characters, 200 lines, and 200 characters per line.",
  ],
  ["model_refused", "Claude declined these lyrics. No result was made."],
  [
    "model_output_truncated",
    "The reply was cut off. Try a shorter part of the song.",
  ],
  [
    "model_output_invalid",
    "Claude's reply did not pass the checks. No result was made. Try again.",
  ],
  [
    "model_unavailable",
    "Claude could not be reached. Check your connection and try again.",
  ],
  [
    "server_not_configured",
    "The server has no Claude API key. Add ANTHROPIC_API_KEY to .env and restart it.",
  ],
]);

// Widened so any code from the server can be looked up; unknown codes get the fallback.
const MESSAGES_BY_ANY_CODE: ReadonlyMap<string, string> = MESSAGES_BY_CODE;

// `details` is used only for `input_too_large`; if it is not valid, the table's message is shown.
export function errorMessageFor(code: string, details?: unknown): string {
  const sizeLimitMessage =
    code === "input_too_large" ? sizeLimitMessageFor(details) : undefined;
  return sizeLimitMessage ?? MESSAGES_BY_ANY_CODE.get(code) ?? FALLBACK_MESSAGE;
}

type SizeLimitName = "maxCharacters" | "maxLines" | "maxLineCharacters";

// A Set, not an object, so names like "toString" are never found.
const SIZE_LIMIT_NAMES: ReadonlySet<string> = new Set<SizeLimitName>([
  "maxCharacters",
  "maxLines",
  "maxLineCharacters",
]);

// Fixed to en-US so numbers read "12,345" whatever the browser's language.
const COUNT_FORMAT = new Intl.NumberFormat("en-US");

function formatCount(count: number): string {
  return COUNT_FORMAT.format(count);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isSizeLimitName(value: unknown): value is SizeLimitName {
  return typeof value === "string" && SIZE_LIMIT_NAMES.has(value);
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

// The sentence naming the size limit the paste broke, or undefined if `details` is not valid.
function sizeLimitMessageFor(details: unknown): string | undefined {
  if (!isRecord(details) || !isSizeLimitName(details.limitHit)) {
    return undefined;
  }
  const limitHit = details.limitHit;
  const measured = details.measured;
  const limit = Object.hasOwn(details, limitHit)
    ? details[limitHit]
    : undefined;
  if (!isPositiveInteger(measured) || !isPositiveInteger(limit)) {
    return undefined;
  }
  switch (limitHit) {
    case "maxCharacters":
      return `The lyrics are too long: ${formatCount(measured)} characters. The limit is ${formatCount(limit)} characters.`;
    case "maxLines":
      return `The lyrics have too many lines: ${formatCount(measured)}. The limit is ${formatCount(limit)} lines.`;
    case "maxLineCharacters":
      return lineTooLongMessage(details.lineNumber, measured, limit);
  }
}

function lineTooLongMessage(
  lineNumber: unknown,
  measured: number,
  limit: number,
): string | undefined {
  if (!isPositiveInteger(lineNumber)) {
    return undefined;
  }
  return `Line ${formatCount(lineNumber)} is too long: ${formatCount(measured)} characters. The limit is ${formatCount(limit)} characters per line. The lyrics may have lost their line breaks.`;
}
