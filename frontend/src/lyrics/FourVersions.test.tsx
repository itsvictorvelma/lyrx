// Checks the result: one group per line, four labeled rows in order, text never HTML.
import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { FourVersions } from "./FourVersions";
import type { Line } from "./types";

const ROW_LABELS = ["Original", "Hiragana", "Romaji", "English"];
const ROW_LABEL_PATTERN = /^(Original|Hiragana|Romaji|English):?$/;
const NOT_VERIFIED_TEXT = "Reading not verified";

function line(index: number, fields: Partial<Omit<Line, "index">> = {}): Line {
  return {
    index,
    original: "",
    hiragana: "",
    romaji: "",
    english: "",
    readingVerified: true,
    ...fields,
  };
}

const sampleLines: Line[] = [
  line(0, {
    original: "星の道",
    hiragana: "ほし の みち",
    romaji: "hoshi no michi",
    english: "The road of stars",
  }),
  line(1, {
    original: "風が 歌う",
    hiragana: "かぜ が うたう",
    romaji: "kaze ga utau",
    english: "The wind sings",
  }),
  line(2),
  line(3, {
    original: "Shine on",
    hiragana: "Shine on",
    romaji: "Shine on",
    english: "Shine on",
  }),
];

function groups(): HTMLElement[] {
  return within(screen.getByRole("list")).getAllByRole("listitem");
}

function labelsIn(group: HTMLElement): string[] {
  return within(group)
    .queryAllByText(ROW_LABEL_PATTERN)
    .map((element) => element.textContent.replace(":", ""));
}

function textOf(element: HTMLElement): string {
  return element.textContent;
}

function groupAt(index: number): HTMLElement {
  const group = groups()[index];
  if (group === undefined) {
    throw new Error(`no group at ${String(index)}`);
  }
  return group;
}

describe("FourVersions groups", () => {
  test("test_ac37_one_group_per_line", () => {
    render(<FourVersions lines={sampleLines} />);

    expect(groups()).toHaveLength(sampleLines.length);
  });

  test("test_ac37_groups_follow_the_line_order", () => {
    render(<FourVersions lines={sampleLines} />);

    expect(textOf(groupAt(0))).toContain("星の道");
    expect(textOf(groupAt(1))).toContain("風が 歌う");
    expect(textOf(groupAt(3))).toContain("Shine on");
  });

  test("test_ac37_each_group_has_the_four_labels_in_order", () => {
    render(<FourVersions lines={sampleLines} />);

    for (const index of [0, 1, 3]) {
      expect(labelsIn(groupAt(index))).toEqual(ROW_LABELS);
    }
  });

  test("test_ac37_each_group_shows_its_four_values_in_label_order", () => {
    render(<FourVersions lines={sampleLines} />);

    const text = textOf(groupAt(1));
    const positions = [
      "風が 歌う",
      "かぜ が うたう",
      "kaze ga utau",
      "The wind sings",
    ].map((value) => text.indexOf(value));
    for (const position of positions) {
      expect(position).toBeGreaterThanOrEqual(0);
    }
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);
    for (const [order, label] of ROW_LABELS.entries()) {
      const labelPosition = text.indexOf(label);
      const valuePosition = positions[order] ?? -1;
      expect(labelPosition).toBeLessThan(valuePosition);
    }
  });

  test("test_ac37_line_without_japanese_shows_its_text_in_all_four_rows", () => {
    render(<FourVersions lines={sampleLines} />);

    expect(within(groupAt(3)).getAllByText("Shine on")).toHaveLength(4);
  });

  test("test_ac37_blank_line_is_a_group_with_no_labels", () => {
    render(<FourVersions lines={sampleLines} />);

    const blank = groupAt(2);
    expect(labelsIn(blank)).toEqual([]);
    expect(textOf(blank).trim()).toBe("");
  });

  test("test_ac37_empty_list_renders_no_groups", () => {
    render(<FourVersions lines={[]} />);

    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });
});

describe("FourVersions Japanese glyphs", () => {
  test("test_ac37_original_and_hiragana_values_are_marked_japanese", () => {
    render(<FourVersions lines={sampleLines} />);

    const group = groupAt(1);
    for (const value of ["風が 歌う", "かぜ が うたう"]) {
      const element = within(group).getByText(value);
      expect(element.closest('[lang="ja"]')).not.toBeNull();
    }
  });

  test("test_ac37_romaji_and_english_values_are_not_marked_japanese", () => {
    render(<FourVersions lines={sampleLines} />);

    const group = groupAt(1);
    for (const value of ["kaze ga utau", "The wind sings"]) {
      const element = within(group).getByText(value);
      expect(element.closest('[lang="ja"]')).toBeNull();
    }
  });
});

describe("FourVersions renders text, never HTML", () => {
  test("test_ac40_bold_markup_shows_literally", () => {
    const { container } = render(
      <FourVersions
        lines={[
          line(0, {
            original: "<b>x</b>",
            hiragana: "ほし",
            romaji: "hoshi",
            english: "<b>x</b>",
          }),
        ]}
      />,
    );

    expect(container.querySelector("b")).toBeNull();
    expect(within(groupAt(0)).getAllByText("<b>x</b>")).toHaveLength(2);
  });

  test("test_ac40_image_markup_shows_literally_and_creates_no_image", () => {
    const markup = '<img src=x onerror="alert(1)">';
    const { container } = render(
      <FourVersions
        lines={[
          line(0, {
            original: markup,
            hiragana: markup,
            romaji: markup,
            english: markup,
          }),
        ]}
      />,
    );

    expect(container.querySelector("img")).toBeNull();
    expect(within(groupAt(0)).getAllByText(markup)).toHaveLength(4);
  });
});

describe("FourVersions reading note", () => {
  const unverifiedLines: Line[] = [
    line(0, {
      original: "君がいる",
      hiragana: "きみ が いた",
      romaji: "kimi ga ita",
      english: "You were there",
      readingVerified: false,
    }),
    line(1, {
      original: "空が 青い",
      hiragana: "そら が あおい",
      romaji: "sora ga aoi",
      english: "The sky is blue",
    }),
  ];

  test("test_ac41_unverified_line_shows_the_note_in_words", () => {
    render(<FourVersions lines={unverifiedLines} />);

    expect(within(groupAt(0)).getByText(NOT_VERIFIED_TEXT)).toBeDefined();
  });

  test("test_ac41_note_sits_in_the_hiragana_row", () => {
    render(<FourVersions lines={unverifiedLines} />);

    const text = textOf(groupAt(0));
    const notePosition = text.indexOf(NOT_VERIFIED_TEXT);
    expect(notePosition).toBeGreaterThan(text.indexOf("Hiragana"));
    expect(notePosition).toBeGreaterThan(text.indexOf("きみ が いた"));
    expect(notePosition).toBeLessThan(text.indexOf("Romaji"));
  });

  test("test_ac41_verified_line_shows_no_note", () => {
    render(<FourVersions lines={unverifiedLines} />);

    expect(within(groupAt(1)).queryByText(NOT_VERIFIED_TEXT)).toBeNull();
    expect(screen.getAllByText(NOT_VERIFIED_TEXT)).toHaveLength(1);
  });

  test("test_ac41_blank_line_shows_no_note", () => {
    render(<FourVersions lines={[line(0)]} />);

    expect(screen.queryByText(NOT_VERIFIED_TEXT)).toBeNull();
  });
});
