// Checks that every server error code maps to the exact message the page shows (spec 001, the page).
import { afterEach, describe, expect, test, vi } from "vitest";
import { errorMessageFor, SERVER_UNREACHABLE_MESSAGE } from "./errorMessages";

const FALLBACK_MESSAGE = "Something went wrong. Try again.";
const AC45_MESSAGE =
  "The lyrics are too long. The limit is 5,000 characters, 200 lines, and 200 characters per line.";
const LIMITS = { maxCharacters: 5000, maxLines: 200, maxLineCharacters: 200 };

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

// Makes the default number format German ("12.345"), as a de-DE browser would.
function useGermanNumberFormatting(): void {
  vi.spyOn(navigator, "language", "get").mockReturnValue("de-DE");
  vi.spyOn(navigator, "languages", "get").mockReturnValue(["de-DE"]);
  const RealNumberFormat = Intl.NumberFormat;
  vi.spyOn(Intl, "NumberFormat").mockImplementation(function (
    locales?: Intl.LocalesArgument,
    options?: Intl.NumberFormatOptions,
  ) {
    return new RealNumberFormat(locales ?? "de-DE", options);
  });
  vi.spyOn(Number.prototype, "toLocaleString").mockImplementation(function (
    this: number,
    locales?: Intl.LocalesArgument,
    options?: Intl.NumberFormatOptions,
  ) {
    return new RealNumberFormat(locales ?? "de-DE", options).format(this);
  });
}

describe("errorMessageFor with size-limit details (AC-48)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test.each([
    [
      "maxCharacters",
      { ...LIMITS, limitHit: "maxCharacters", measured: 5002 },
      "The lyrics are too long: 5,002 characters. The limit is 5,000 characters.",
    ],
    [
      "maxLines",
      { ...LIMITS, limitHit: "maxLines", measured: 201 },
      "The lyrics have too many lines: 201. The limit is 200 lines.",
    ],
    [
      "maxLineCharacters",
      {
        ...LIMITS,
        limitHit: "maxLineCharacters",
        measured: 2700,
        lineNumber: 1,
      },
      "Line 1 is too long: 2,700 characters. The limit is 200 characters per line. The lyrics may have lost their line breaks.",
    ],
  ])(
    "test_ac48_7_limit_hit_%s_has_its_exact_sentence",
    (_limitHit, details, message) => {
      expect(errorMessageFor("input_too_large", details)).toBe(message);
    },
  );

  test.each([
    [
      "maxCharacters",
      {
        ...LIMITS,
        maxCharacters: 6000,
        limitHit: "maxCharacters",
        measured: 6001,
      },
      "The lyrics are too long: 6,001 characters. The limit is 6,000 characters.",
    ],
    [
      "maxLines",
      { ...LIMITS, maxLines: 1500, limitHit: "maxLines", measured: 1501 },
      "The lyrics have too many lines: 1,501. The limit is 1,500 lines.",
    ],
    [
      "maxLineCharacters",
      {
        ...LIMITS,
        maxLineCharacters: 300,
        limitHit: "maxLineCharacters",
        measured: 301,
        lineNumber: 1024,
      },
      "Line 1,024 is too long: 301 characters. The limit is 300 characters per line. The lyrics may have lost their line breaks.",
    ],
  ])(
    "test_ac48_limit_in_the_%s_sentence_comes_from_its_max_value",
    (_limitHit, details, message) => {
      expect(errorMessageFor("input_too_large", details)).toBe(message);
    },
  );

  test("test_ac48_8_measured_12345_has_commas_in_a_german_browser", () => {
    useGermanNumberFormatting();
    expect((12345).toLocaleString()).toBe("12.345");
    expect(new Intl.NumberFormat().format(12345)).toBe("12.345");

    const message = errorMessageFor("input_too_large", {
      ...LIMITS,
      limitHit: "maxCharacters",
      measured: 12345,
    });

    expect(message).toBe(
      "The lyrics are too long: 12,345 characters. The limit is 5,000 characters.",
    );
  });

  test.each([
    ["no details", undefined],
    ["details with only the three max keys", { ...LIMITS }],
    ["limitHit bytes", { ...LIMITS, limitHit: "bytes", measured: 5002 }],
    [
      "measured as a string",
      { ...LIMITS, limitHit: "maxCharacters", measured: "5,002" },
    ],
    ["measured -3", { ...LIMITS, limitHit: "maxCharacters", measured: -3 }],
    ["measured 2.5", { ...LIMITS, limitHit: "maxCharacters", measured: 2.5 }],
    [
      "maxLineCharacters with no lineNumber",
      { ...LIMITS, limitHit: "maxLineCharacters", measured: 2700 },
    ],
  ])("test_ac48_9_%s_gets_the_ac45_message", (_name, details) => {
    expect(errorMessageFor("input_too_large", details)).toBe(AC45_MESSAGE);
  });

  test.each([
    ["details that are not an object", "maxCharacters"],
    ["details that are a list", [5000, 200, 200]],
    ["details that are null", null],
    ["measured 0", { ...LIMITS, limitHit: "maxCharacters", measured: 0 }],
    [
      "a missing matching max value",
      {
        maxLines: 200,
        maxLineCharacters: 200,
        limitHit: "maxCharacters",
        measured: 5002,
      },
    ],
    [
      "a matching max value that is a string",
      { ...LIMITS, maxLines: "200", limitHit: "maxLines", measured: 201 },
    ],
    [
      "a matching max value of 0",
      {
        ...LIMITS,
        maxLineCharacters: 0,
        limitHit: "maxLineCharacters",
        measured: 2700,
        lineNumber: 1,
      },
    ],
    [
      "lineNumber 0",
      {
        ...LIMITS,
        limitHit: "maxLineCharacters",
        measured: 2700,
        lineNumber: 0,
      },
    ],
    [
      "lineNumber 1.5",
      {
        ...LIMITS,
        limitHit: "maxLineCharacters",
        measured: 2700,
        lineNumber: 1.5,
      },
    ],
    [
      "a limitHit inherited from Object",
      { ...LIMITS, limitHit: "toString", measured: 5002 },
    ],
  ])("test_ac48_fallback_rule_%s_gets_the_ac45_message", (_name, details) => {
    expect(errorMessageFor("input_too_large", details)).toBe(AC45_MESSAGE);
  });

  test.each([
    ["limitHit", { ...LIMITS, limitHit: "<b>x</b>", measured: 5002 }],
    [
      "measured",
      { ...LIMITS, limitHit: "maxCharacters", measured: "<b>x</b>" },
    ],
  ])("test_ac48_10_markup_in_%s_gets_the_ac45_message", (_field, details) => {
    expect(errorMessageFor("input_too_large", details)).toBe(AC45_MESSAGE);
  });

  test("test_ac48_details_on_another_code_do_not_change_its_message", () => {
    const details = { ...LIMITS, limitHit: "maxCharacters", measured: 5002 };

    expect(errorMessageFor("no_japanese", details)).toBe(
      "No Japanese text found. Paste Japanese lyrics.",
    );
  });
});
