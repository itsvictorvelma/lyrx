// Checks the paste form: labeled text area, the submit button, and the waiting status.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { PasteForm } from "./PasteForm";

const WAITING_TEXT = "Working on your lyrics…";

function renderForm(waiting = false) {
  const onSubmit = vi.fn<(lyrics: string) => void>();
  render(<PasteForm waiting={waiting} onSubmit={onSubmit} />);
  return {
    onSubmit,
    textArea: screen.getByLabelText("Japanese lyrics"),
    button: screen.getByRole("button", { name: "Get four versions" }),
  };
}

describe("PasteForm controls", () => {
  test("test_ac34_has_a_labeled_text_area_and_the_button", () => {
    const { textArea, button } = renderForm();

    expect(textArea.tagName).toBe("TEXTAREA");
    expect(screen.getByRole("textbox", { name: "Japanese lyrics" })).toBe(
      textArea,
    );
    expect(button).toBeDefined();
  });

  test("test_ac34_button_is_disabled_while_the_text_area_is_empty", () => {
    const { button } = renderForm();

    expect(button).toHaveProperty("disabled", true);
  });

  test("test_ac34_button_is_disabled_for_whitespace_only", async () => {
    const user = userEvent.setup();
    const { textArea, button } = renderForm();

    await user.click(textArea);
    await user.paste("   \n\t \n  ");

    expect(button).toHaveProperty("disabled", true);
  });

  test("test_ac34_button_is_enabled_once_lyrics_are_typed", async () => {
    const user = userEvent.setup();
    const { textArea, button } = renderForm();

    await user.click(textArea);
    await user.paste("月の光");

    expect(button).toHaveProperty("disabled", false);
  });

  test("test_ac34_tab_moves_focus_to_the_text_area_then_the_button", async () => {
    const user = userEvent.setup();
    const { textArea, button } = renderForm();
    await user.click(textArea);
    await user.paste("月の光");
    textArea.blur();

    await user.tab();
    expect(document.activeElement).toBe(textArea);
    await user.tab();
    expect(document.activeElement).toBe(button);
  });
});

describe("PasteForm submit", () => {
  test("test_ac35_clicking_the_button_submits_the_text_as_typed", async () => {
    const user = userEvent.setup();
    const { textArea, button, onSubmit } = renderForm();
    const lyrics = "月の光\n\n  夜が 明ける";

    await user.click(textArea);
    await user.paste(lyrics);
    await user.click(button);

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith(lyrics);
  });

  test("test_ac35_submit_does_not_reload_the_page", async () => {
    const user = userEvent.setup();
    const { textArea, button } = renderForm();
    const submitted = vi.fn((event: SubmitEvent) => event.defaultPrevented);
    document.addEventListener("submit", submitted);

    await user.click(textArea);
    await user.paste("月の光");
    await user.click(button);
    document.removeEventListener("submit", submitted);

    // When the button sits in a form, React must cancel the browser's own submit.
    for (const result of submitted.mock.results) {
      expect(result.value).toBe(true);
    }
  });
});

describe("PasteForm waiting", () => {
  test("test_ac36_waiting_disables_the_button_even_with_text", async () => {
    const onSubmit = vi.fn<(lyrics: string) => void>();
    const user = userEvent.setup();
    const { rerender } = render(
      <PasteForm waiting={false} onSubmit={onSubmit} />,
    );
    await user.click(screen.getByLabelText("Japanese lyrics"));
    await user.paste("月の光");

    rerender(<PasteForm waiting={true} onSubmit={onSubmit} />);

    const button = screen.getByRole("button", { name: "Get four versions" });
    expect(button).toHaveProperty("disabled", true);
    await user.click(button);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test("test_ac36_waiting_shows_the_status_in_a_polite_live_region", () => {
    renderForm(true);

    const status = screen.getByText(WAITING_TEXT);
    const liveRegion = status.closest('[aria-live="polite"], [role="status"]');
    expect(liveRegion).not.toBeNull();
  });

  test("test_ac36_not_waiting_shows_no_status_text", () => {
    renderForm(false);

    expect(screen.queryByText(WAITING_TEXT)).toBeNull();
  });

  test("test_ac36_waiting_keeps_the_typed_text", async () => {
    const onSubmit = vi.fn<(lyrics: string) => void>();
    const user = userEvent.setup();
    const { rerender } = render(
      <PasteForm waiting={false} onSubmit={onSubmit} />,
    );
    await user.click(screen.getByLabelText("Japanese lyrics"));
    await user.paste("月の光");

    rerender(<PasteForm waiting={true} onSubmit={onSubmit} />);

    expect(screen.getByLabelText("Japanese lyrics")).toHaveProperty(
      "value",
      "月の光",
    );
  });
});
