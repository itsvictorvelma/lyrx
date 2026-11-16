// Checks that the Lyrx page renders its heading.
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { App } from "./App";

test("shows the Lyrx heading", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "Lyrx" })).toBeDefined();
});
