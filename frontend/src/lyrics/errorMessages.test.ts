// Checks that every server error code maps to the exact message the page shows (spec 001, the page).
import { describe, expect, test } from "vitest";
import { errorMessageFor, SERVER_UNREACHABLE_MESSAGE } from "./errorMessages";

const FALLBACK_MESSAGE = "Something went wrong. Try again.";

// The spec writes the variable and file name in code style; the page may show them with or
// without backticks, so the comparison ignores backticks.
function withoutBackticks(text: string): string {
  return text.replaceAll("`", "");
}

describe("errorMessageFor", () => {
  test.each([
    ["empty_input", "Paste some lyrics first."],
    ["no_japanese", "No Japanese text found. Paste Japanese lyrics."],
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
  ])("test_ac38_code_%s_has_its_page_message", (code, message) => {
    expect(errorMessageFor(code)).toBe(message);
  });

  test("test_ac38_ac45_input_too_large_uses_the_per_line_limit_text", () => {
    expect(errorMessageFor("input_too_large")).toBe(
      "The lyrics are too long. The limit is 5,000 characters, 200 lines, and 200 characters per line.",
    );
  });

  test("test_ac38_server_not_configured_names_the_key_and_the_env_file", () => {
    expect(withoutBackticks(errorMessageFor("server_not_configured"))).toBe(
      "The server has no Claude API key. Add ANTHROPIC_API_KEY to .env and restart it.",
    );
  });

  test.each([
    "invalid_request",
    "host_not_allowed",
    "not_found",
    "method_not_allowed",
    "internal_error",
    "made_up_code",
    "",
  ])("test_ac38_other_code_%j_gets_the_fallback_message", (code) => {
    expect(errorMessageFor(code)).toBe(FALLBACK_MESSAGE);
  });

  test("test_ac38_object_prototype_names_are_not_messages", () => {
    expect(errorMessageFor("toString")).toBe(FALLBACK_MESSAGE);
    expect(errorMessageFor("constructor")).toBe(FALLBACK_MESSAGE);
    expect(errorMessageFor("__proto__")).toBe(FALLBACK_MESSAGE);
  });
});

test("test_ac39_server_unreachable_message", () => {
  expect(SERVER_UNREACHABLE_MESSAGE).toBe(
    "Could not reach the Lyrx server. Is it running?",
  );
});
