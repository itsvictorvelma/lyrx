// Checks the whole page: paste, one request, waiting, result, and every error message.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { App } from "./App";
import type { Line } from "./lyrics/types";

const WAITING_TEXT = "Working on your lyrics…";
const FALLBACK_MESSAGE = "Something went wrong. Try again.";
const PASTED_LYRICS = "星の道\n\n風が 歌う";

const fakeFetch = vi.fn<typeof fetch>();

beforeEach(() => {
  fakeFetch.mockReset();
  vi.stubGlobal("fetch", fakeFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const resultLines: Line[] = [
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
  {
    index: 2,
    original: "風が 歌う",
    hiragana: "かぜ が うたう",
    romaji: "kaze ga utau",
    english: "The wind sings",
    readingVerified: true,
  },
];

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function errorResponse(status: number, code: string): Response {
  return jsonResponse(status, {
    code,
    message: "A server message the page does not show.",
  });
}

function deferredResponse(): {
  promise: Promise<Response>;
  resolve: (r: Response) => void;
} {
  let resolve: (response: Response) => void = () => undefined;
  const promise = new Promise<Response>((resolveResponse) => {
    resolve = resolveResponse;
  });
  return { promise, resolve };
}

function textArea(): HTMLElement {
  return screen.getByLabelText("Japanese lyrics");
}

function submitButton(): HTMLElement {
  return screen.getByRole("button", { name: "Get four versions" });
}

async function pasteAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  lyrics = PASTED_LYRICS,
) {
  await user.click(textArea());
  await user.clear(textArea());
  await user.paste(lyrics);
  await user.click(submitButton());
}

function withoutBackticks(text: string): string {
  return text.replaceAll("`", "");
}

describe("App page", () => {
  test("shows the Lyrx heading", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Lyrx" })).toBeDefined();
  });

  test("test_ac34_page_has_the_labeled_text_area_and_a_disabled_button", () => {
    render(<App />);

    expect(textArea().tagName).toBe("TEXTAREA");
    expect(submitButton()).toHaveProperty("disabled", true);
  });

  test("test_ac34_page_has_no_link_field", () => {
    render(<App />);

    expect(screen.getAllByRole("textbox")).toHaveLength(1);
  });
});

describe("App request", () => {
  test("test_ac35_submit_sends_one_post_with_the_pasted_lyrics", async () => {
    fakeFetch.mockResolvedValue(jsonResponse(200, { lines: resultLines }));
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);
    await screen.findByRole("list");

    expect(fakeFetch).toHaveBeenCalledTimes(1);
    const call = fakeFetch.mock.calls[0];
    expect(call?.[0]).toBe("/api/versions");
    expect(call?.[1]?.method).toBe("POST");
    const sentText = call?.[1]?.body;
    if (typeof sentText !== "string") {
      throw new Error("the request body is not a JSON string");
    }
    const sentBody: unknown = JSON.parse(sentText);
    expect(sentBody).toEqual({ lyrics: PASTED_LYRICS });
  });

  test("test_ac36_pending_request_disables_the_button_and_shows_the_status", async () => {
    const pending = deferredResponse();
    fakeFetch.mockReturnValue(pending.promise);
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);

    expect(submitButton()).toHaveProperty("disabled", true);
    const status = await screen.findByText(WAITING_TEXT);
    expect(
      status.closest('[aria-live="polite"], [role="status"]'),
    ).not.toBeNull();
  });

  test("test_ac36_clicking_again_while_pending_sends_no_second_request", async () => {
    const pending = deferredResponse();
    fakeFetch.mockReturnValue(pending.promise);
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);
    await user.click(submitButton());
    await user.click(submitButton());

    expect(fakeFetch).toHaveBeenCalledTimes(1);
  });

  test("test_ac36_status_goes_away_and_button_returns_when_the_reply_arrives", async () => {
    const pending = deferredResponse();
    fakeFetch.mockReturnValue(pending.promise);
    const user = userEvent.setup();
    render(<App />);
    await pasteAndSubmit(user);
    await screen.findByText(WAITING_TEXT);

    pending.resolve(jsonResponse(200, { lines: resultLines }));
    await screen.findByRole("list");

    expect(screen.queryByText(WAITING_TEXT)).toBeNull();
    expect(submitButton()).toHaveProperty("disabled", false);
  });
});

describe("App result", () => {
  test("test_ac37_success_shows_one_group_per_line_with_labels_in_order", async () => {
    fakeFetch.mockResolvedValue(jsonResponse(200, { lines: resultLines }));
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);

    const list = await screen.findByRole("list");
    const groups = within(list).getAllByRole("listitem");
    expect(groups).toHaveLength(3);
    const [first, blank, third] = groups;
    for (const group of [first, third]) {
      if (group === undefined) throw new Error("missing group");
      const labels = within(group)
        .getAllByText(/^(Original|Hiragana|Romaji|English):?$/)
        .map((element) => element.textContent.replace(":", ""));
      expect(labels).toEqual(["Original", "Hiragana", "Romaji", "English"]);
    }
    expect(first?.textContent).toContain("hoshi no michi");
    expect(third?.textContent).toContain("The wind sings");
    expect(blank?.textContent.trim()).toBe("");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("test_ac40_markup_in_a_reply_renders_as_text", async () => {
    fakeFetch.mockResolvedValue(
      jsonResponse(200, {
        lines: [
          {
            index: 0,
            original: "<b>x</b>",
            hiragana: "ほし",
            romaji: "hoshi",
            english: '<img src=x onerror="alert(1)">',
            readingVerified: true,
          },
        ],
      }),
    );
    const user = userEvent.setup();
    const { container } = render(<App />);

    await pasteAndSubmit(user, "星");
    await screen.findByRole("list");

    expect(container.querySelector("b")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("<b>x</b>")).toBeDefined();
    expect(screen.getByText('<img src=x onerror="alert(1)">')).toBeDefined();
  });

  test("test_ac41_unverified_reading_is_noted_in_words", async () => {
    fakeFetch.mockResolvedValue(
      jsonResponse(200, {
        lines: [
          {
            index: 0,
            original: "君がいる",
            hiragana: "きみ が いた",
            romaji: "kimi ga ita",
            english: "You were there",
            readingVerified: false,
          },
        ],
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user, "君がいる");

    expect(await screen.findByText("Reading not verified")).toBeDefined();
  });
});

describe("App errors", () => {
  test.each([
    ["empty_input", 400, "Paste some lyrics first."],
    ["no_japanese", 400, "No Japanese text found. Paste Japanese lyrics."],
    [
      "input_too_large",
      413,
      "The lyrics are too long. The limit is 5,000 characters, 200 lines, and 200 characters per line.",
    ],
    ["model_refused", 502, "Claude declined these lyrics. No result was made."],
    [
      "model_output_truncated",
      502,
      "The reply was cut off. Try a shorter part of the song.",
    ],
    [
      "model_output_invalid",
      502,
      "Claude's reply did not pass the checks. No result was made. Try again.",
    ],
    [
      "model_unavailable",
      503,
      "Claude could not be reached. Check your connection and try again.",
    ],
    [
      "server_not_configured",
      503,
      "The server has no Claude API key. Add ANTHROPIC_API_KEY to .env and restart it.",
    ],
    ["invalid_request", 400, FALLBACK_MESSAGE],
    ["host_not_allowed", 403, FALLBACK_MESSAGE],
    ["not_found", 404, FALLBACK_MESSAGE],
    ["method_not_allowed", 405, FALLBACK_MESSAGE],
    ["internal_error", 500, FALLBACK_MESSAGE],
    ["made_up_code", 500, FALLBACK_MESSAGE],
  ])(
    "test_ac38_code_%s_shows_its_message_in_an_alert_and_keeps_the_text",
    async (code, status, message) => {
      fakeFetch.mockResolvedValue(errorResponse(status, code));
      const user = userEvent.setup();
      render(<App />);

      await pasteAndSubmit(user);

      const alert = await screen.findByRole("alert");
      const alertText = withoutBackticks(alert.textContent);
      expect(alertText).toContain(message);
      expect(alertText).toContain("Error:");
      expect(screen.queryByRole("list")).toBeNull();
      expect(textArea()).toHaveProperty("value", PASTED_LYRICS);
    },
  );

  test("test_ac38_non_json_error_reply_shows_the_fallback_message", async () => {
    fakeFetch.mockResolvedValue(
      new Response("<html>Bad gateway</html>", { status: 502 }),
    );
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(FALLBACK_MESSAGE);
    expect(alert.textContent).not.toContain("Bad gateway");
  });

  test("test_ac38_body_read_failure_shows_the_fallback_message", async () => {
    const response = jsonResponse(200, { lines: resultLines });
    const bodyError = new TypeError("The body stream broke");
    vi.spyOn(response, "text").mockRejectedValue(bodyError);
    vi.spyOn(response, "json").mockRejectedValue(bodyError);
    fakeFetch.mockResolvedValue(response);
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(FALLBACK_MESSAGE);
    expect(alert.textContent).not.toContain("Could not reach");
    expect(alert.textContent).not.toContain("body stream");
    expect(screen.queryByRole("list")).toBeNull();
  });

  test("test_ac38_reply_with_a_gap_in_indexes_shows_the_fallback_message", async () => {
    const [first, , third] = resultLines;
    fakeFetch.mockResolvedValue(jsonResponse(200, { lines: [first, third] }));
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(FALLBACK_MESSAGE);
    expect(screen.queryByRole("list")).toBeNull();
  });

  test("test_ac38_error_after_a_result_clears_the_result", async () => {
    fakeFetch
      .mockResolvedValueOnce(jsonResponse(200, { lines: resultLines }))
      .mockResolvedValueOnce(errorResponse(502, "model_refused"));
    const user = userEvent.setup();
    render(<App />);
    await pasteAndSubmit(user);
    await screen.findByRole("list");

    await user.click(submitButton());

    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.queryByRole("list")).toBeNull();
  });

  test("test_ac38_new_submit_clears_the_previous_error_while_waiting", async () => {
    const pending = deferredResponse();
    fakeFetch
      .mockResolvedValueOnce(errorResponse(400, "no_japanese"))
      .mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    render(<App />);
    await pasteAndSubmit(user);
    await screen.findByRole("alert");

    await user.click(submitButton());

    await screen.findByText(WAITING_TEXT);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("list")).toBeNull();
  });

  test("test_ac39_rejected_fetch_shows_the_server_unreachable_message", async () => {
    fakeFetch.mockRejectedValue(new TypeError("Failed to fetch"));
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(
      "Could not reach the Lyrx server. Is it running?",
    );
    expect(alert.textContent).toContain("Error:");
    expect(alert.textContent).not.toContain("Failed to fetch");
    expect(textArea()).toHaveProperty("value", PASTED_LYRICS);
  });
});
