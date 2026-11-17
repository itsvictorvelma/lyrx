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

export function errorMessageFor(code: string): string {
  return MESSAGES_BY_ANY_CODE.get(code) ?? FALLBACK_MESSAGE;
}
