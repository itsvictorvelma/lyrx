// Checks the whole page: paste, one request, waiting, result, and every error message.
import { render, screen, waitFor, within } from "@testing-library/react";
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

describe("App size-limit errors (AC-48)", () => {
  const AC45_MESSAGE =
    "The lyrics are too long. The limit is 5,000 characters, 200 lines, and 200 characters per line.";
  const LIMITS = { maxCharacters: 5000, maxLines: 200, maxLineCharacters: 200 };

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function tooLargeResponse(details?: unknown): Response {
    return jsonResponse(413, {
      code: "input_too_large",
      message: "A server sentence the page builds itself.",
      ...(details === undefined ? {} : { details }),
    });
  }

  async function submitAndReadAlert(reply: Response): Promise<string> {
    fakeFetch.mockResolvedValue(reply);
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);

    const alert = await screen.findByRole("alert");
    return alert.textContent;
  }

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
    "test_ac48_7_limit_hit_%s_shows_its_sentence_and_keeps_the_text",
    async (_limitHit, details, message) => {
      const alertText = await submitAndReadAlert(tooLargeResponse(details));

      expect(alertText).toContain(message);
      expect(alertText).not.toContain(AC45_MESSAGE);
      expect(alertText).not.toContain("A server sentence");
      expect(screen.queryByRole("list")).toBeNull();
      expect(textArea()).toHaveProperty("value", PASTED_LYRICS);
    },
  );

  test("test_ac48_8_measured_12345_shows_as_12_345_in_a_german_browser", async () => {
    useGermanNumberFormatting();
    expect((12345).toLocaleString()).toBe("12.345");

    const alertText = await submitAndReadAlert(
      tooLargeResponse({
        ...LIMITS,
        limitHit: "maxCharacters",
        measured: 12345,
      }),
    );

    expect(alertText).toContain(
      "The lyrics are too long: 12,345 characters. The limit is 5,000 characters.",
    );
    expect(alertText).not.toContain("12.345");
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
  ])("test_ac48_9_%s_shows_the_ac45_message", async (_name, details) => {
    const alertText = await submitAndReadAlert(tooLargeResponse(details));

    expect(alertText).toContain(AC45_MESSAGE);
    expect(screen.queryByRole("list")).toBeNull();
    expect(textArea()).toHaveProperty("value", PASTED_LYRICS);
  });

  test.each([
    ["limitHit", { ...LIMITS, limitHit: "<b>x</b>", measured: 5002 }],
    [
      "measured",
      { ...LIMITS, limitHit: "maxCharacters", measured: "<b>x</b>" },
    ],
  ])(
    "test_ac48_10_markup_in_%s_creates_no_element_and_shows_the_ac45_message",
    async (_field, details) => {
      fakeFetch.mockResolvedValue(tooLargeResponse(details));
      const user = userEvent.setup();
      const { container } = render(<App />);

      await pasteAndSubmit(user);
      const alert = await screen.findByRole("alert");

      expect(container.querySelector("b")).toBeNull();
      expect(alert.textContent).toContain(AC45_MESSAGE);
      expect(alert.textContent).not.toContain("<b>x</b>");
    },
  );
});

describe("App result heading (T9 accessibility)", () => {
  function line(index: number, original: string): Line {
    return {
      index,
      original,
      hiragana: "ほし",
      romaji: "hoshi",
      english: "Star",
      readingVerified: true,
    };
  }

  function resultHeading(): HTMLElement {
    return screen.getByRole("heading", { level: 2, name: /Four versions/ });
  }

  test("test_t9_a11y_result_heading_appears_above_the_list_and_takes_focus", async () => {
    fakeFetch.mockResolvedValue(jsonResponse(200, { lines: resultLines }));
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);
    const list = await screen.findByRole("list");

    const heading = resultHeading();
    expect(
      heading.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(document.activeElement).toBe(heading);
  });

  test("test_t9_a11y_result_heading_counts_two_lines", async () => {
    fakeFetch.mockResolvedValue(
      jsonResponse(200, { lines: [line(0, "星"), line(1, "月")] }),
    );
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user, "星\n月");
    await screen.findByRole("list");

    expect(resultHeading().textContent).toContain("2 lines");
  });

  test("test_t9_a11y_result_heading_counts_blank_lines_too", async () => {
    fakeFetch.mockResolvedValue(jsonResponse(200, { lines: resultLines }));
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);
    await screen.findByRole("list");

    expect(resultLines.filter((line) => line.original === "")).toHaveLength(1);
    expect(resultHeading().textContent).toContain("3 lines");
  });

  test("test_t9_a11y_result_heading_says_1_line_for_one_line", async () => {
    fakeFetch.mockResolvedValue(jsonResponse(200, { lines: [line(0, "星")] }));
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user, "星");
    await screen.findByRole("list");

    const text = resultHeading().textContent;
    expect(text).toContain("1 line");
    expect(text).not.toContain("1 lines");
  });

  test("test_t9_a11y_no_result_heading_while_idle", () => {
    render(<App />);

    expect(screen.queryByRole("heading", { level: 2 })).toBeNull();
  });

  test("test_t9_a11y_no_result_heading_while_waiting", async () => {
    fakeFetch.mockReturnValue(deferredResponse().promise);
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);
    await screen.findByText(WAITING_TEXT);

    expect(screen.queryByRole("heading", { level: 2 })).toBeNull();
  });

  test("test_t9_a11y_no_result_heading_on_error", async () => {
    fakeFetch.mockResolvedValue(errorResponse(502, "model_refused"));
    const user = userEvent.setup();
    render(<App />);

    await pasteAndSubmit(user);
    await screen.findByRole("alert");

    expect(screen.queryByRole("heading", { level: 2 })).toBeNull();
  });

  test("test_t9_a11y_second_result_moves_focus_to_the_heading_again", async () => {
    fakeFetch
      .mockResolvedValueOnce(jsonResponse(200, { lines: resultLines }))
      .mockResolvedValueOnce(jsonResponse(200, { lines: [line(0, "星")] }));
    const user = userEvent.setup();
    render(<App />);
    await pasteAndSubmit(user);
    await screen.findByRole("list");

    await user.click(submitButton());
    await waitFor(() => {
      expect(screen.getAllByRole("listitem")).toHaveLength(1);
    });

    expect(document.activeElement).toBe(resultHeading());
  });

  test.each(["{Enter}", " "])(
    "test_t9_a11y_keyboard_submit_with_%j_leaves_focus_on_the_heading",
    async (key) => {
      fakeFetch.mockResolvedValue(jsonResponse(200, { lines: resultLines }));
      const user = userEvent.setup();
      render(<App />);
      await user.click(textArea());
      await user.paste(PASTED_LYRICS);
      submitButton().focus();
      expect(document.activeElement).toBe(submitButton());

      await user.keyboard(key);
      await screen.findByRole("list");

      expect(fakeFetch).toHaveBeenCalledTimes(1);
      expect(document.activeElement).not.toBe(document.body);
      expect(document.activeElement).toBe(resultHeading());
    },
  );
});

describe("App focus after an error (T9 accessibility)", () => {
  test.each([
    ["an error reply", () => errorResponse(400, "no_japanese")],
    [
      "a rejected fetch",
      () => Promise.reject(new TypeError("Failed to fetch")),
    ],
  ])(
    "test_t9_a11y_mouse_submit_then_%s_focuses_the_paste_box",
    async (_name, reply) => {
      fakeFetch.mockImplementation(() => Promise.resolve(reply()));
      const user = userEvent.setup();
      render(<App />);

      await pasteAndSubmit(user);
      await screen.findByRole("alert");

      expect(document.activeElement).toBe(textArea());
      expect(textArea()).toHaveProperty("value", PASTED_LYRICS);
    },
  );

  test.each([
    ["an error reply", () => errorResponse(400, "no_japanese")],
    [
      "a rejected fetch",
      () => Promise.reject(new TypeError("Failed to fetch")),
    ],
  ])(
    "test_t9_a11y_keyboard_submit_then_%s_focuses_the_paste_box",
    async (_name, reply) => {
      fakeFetch.mockImplementation(() => Promise.resolve(reply()));
      const user = userEvent.setup();
      render(<App />);
      await user.click(textArea());
      await user.paste(PASTED_LYRICS);
      submitButton().focus();

      await user.keyboard("{Enter}");
      await screen.findByRole("alert");

      expect(fakeFetch).toHaveBeenCalledTimes(1);
      expect(document.activeElement).toBe(textArea());
      expect(textArea()).toHaveProperty("value", PASTED_LYRICS);
    },
  );
});
