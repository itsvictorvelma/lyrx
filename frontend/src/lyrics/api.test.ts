// Checks getFourVersions: one JSON POST to /api/versions and a checked, discriminated result.
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { getFourVersions } from "./api";
import { errorMessageFor } from "./errorMessages";
import type { Line } from "./types";

const fakeFetch = vi.fn<typeof fetch>();

beforeEach(() => {
  fakeFetch.mockReset();
  vi.stubGlobal("fetch", fakeFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function onlyFetchCall(): { url: unknown; init: RequestInit | undefined } {
  expect(fakeFetch).toHaveBeenCalledTimes(1);
  const call = fakeFetch.mock.calls[0];
  if (call === undefined) {
    throw new Error("fetch was not called");
  }
  return { url: call[0], init: call[1] };
}

const inventedLines: Line[] = [
  {
    index: 0,
    original: "星の道",
    hiragana: "ほし の みち",
    romaji: "hoshi no michi",
    english: "The road of stars",
    readingVerified: true,
  },
  {
    index: 1,
    original: "",
    hiragana: "",
    romaji: "",
    english: "",
    readingVerified: true,
  },
];

// One well-formed reply line with the given index.
function replyLine(index: number): Line {
  return {
    index,
    original: "星",
    hiragana: "ほし",
    romaji: "hoshi",
    english: "Star",
    readingVerified: true,
  };
}

describe("getFourVersions request", () => {
  test("test_ac35_sends_one_post_to_api_versions_with_lyrics_as_json", async () => {
    fakeFetch.mockResolvedValue(jsonResponse(200, { lines: inventedLines }));
    const lyrics = "星の道\n\n風が 歌う";

    await getFourVersions(lyrics);

    const { url, init } = onlyFetchCall();
    expect(url).toBe("/api/versions");
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("Content-Type")).toContain(
      "application/json",
    );
    const sentText = init?.body;
    if (typeof sentText !== "string") {
      throw new Error("the request body is not a JSON string");
    }
    const sentBody: unknown = JSON.parse(sentText);
    expect(sentBody).toEqual({ lyrics });
  });
});

describe("getFourVersions result", () => {
  test("test_ac37_success_returns_the_lines", async () => {
    fakeFetch.mockResolvedValue(jsonResponse(200, { lines: inventedLines }));

    const result = await getFourVersions("星の道");

    expect(result).toEqual({ kind: "lines", lines: inventedLines });
  });

  test("test_ac38_error_shape_returns_its_code", async () => {
    fakeFetch.mockResolvedValue(
      jsonResponse(400, {
        code: "no_japanese",
        message: "No Japanese text was found.",
      }),
    );

    const result = await getFourVersions("only English here");

    expect(result).toEqual({ kind: "error", code: "no_japanese" });
  });

  test("test_ac38_error_with_details_returns_its_code", async () => {
    fakeFetch.mockResolvedValue(
      jsonResponse(413, {
        code: "input_too_large",
        message: "The lyrics are too long.",
        details: { maxCharacters: 5000, maxLines: 200, maxLineCharacters: 200 },
      }),
    );

    const result = await getFourVersions("星の道");

    expect(result).toEqual({ kind: "error", code: "input_too_large" });
  });

  test("test_ac38_unknown_code_leads_to_the_fallback_message", async () => {
    fakeFetch.mockResolvedValue(
      jsonResponse(500, { code: "made_up_code", message: "Invented failure." }),
    );

    const result = await getFourVersions("星の道");

    if (result.kind !== "error") {
      throw new Error(`expected an error result, got ${result.kind}`);
    }
    expect(errorMessageFor(result.code)).toBe(
      "Something went wrong. Try again.",
    );
  });

  test.each([
    ["an HTML error page", 502, "<html><body>Bad gateway</body></html>"],
    ["an empty error body", 500, ""],
    ["JSON without a code", 500, JSON.stringify({ message: "no code here" })],
    [
      "a code that is not a string",
      400,
      JSON.stringify({ code: 42, message: "number" }),
    ],
    ["a 200 that is not JSON", 200, "not json at all"],
    [
      "a 200 whose lines are not a list",
      200,
      JSON.stringify({ lines: "nope" }),
    ],
    [
      "a 200 whose line misses a field",
      200,
      JSON.stringify({
        lines: [
          { index: 0, original: "星", hiragana: "ほし", romaji: "hoshi" },
        ],
      }),
    ],
    [
      "a 200 whose readingVerified is not a boolean",
      200,
      JSON.stringify({
        lines: [{ ...replyLine(0), readingVerified: "yes" }],
      }),
    ],
    [
      "a 200 with a non-integer index",
      200,
      JSON.stringify({ lines: [replyLine(0), replyLine(1.5)] }),
    ],
    [
      "a 200 with a repeated index",
      200,
      JSON.stringify({ lines: [replyLine(0), replyLine(0)] }),
    ],
    [
      "a 200 with a gap in the indexes",
      200,
      JSON.stringify({ lines: [replyLine(0), replyLine(2)] }),
    ],
    [
      "a 200 whose indexes do not start at 0",
      200,
      JSON.stringify({ lines: [replyLine(1), replyLine(2)] }),
    ],
  ])("test_ac38_%s_is_unreadable", async (_name, status, body) => {
    fakeFetch.mockResolvedValue(new Response(body, { status }));

    const result = await getFourVersions("星の道");

    expect(result).toEqual({ kind: "unreadable" });
  });

  test("test_ac38_body_read_failure_is_unreadable_not_unreachable", async () => {
    const response = jsonResponse(200, { lines: inventedLines });
    const bodyError = new TypeError("The body stream broke");
    vi.spyOn(response, "text").mockRejectedValue(bodyError);
    vi.spyOn(response, "json").mockRejectedValue(bodyError);
    fakeFetch.mockResolvedValue(response);

    const result = await getFourVersions("星の道");

    expect(result).toEqual({ kind: "unreadable" });
  });

  test("test_ac39_rejected_fetch_returns_unreachable", async () => {
    fakeFetch.mockRejectedValue(new TypeError("Failed to fetch"));

    const result = await getFourVersions("星の道");

    expect(result).toEqual({ kind: "unreachable" });
  });
});
