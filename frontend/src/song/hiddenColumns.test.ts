// Checks that hidden columns are remembered on this browser and survive blocked storage.
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import {
  cellKey,
  storedHiddenColumns,
  useHiddenColumns,
} from "./hiddenColumns";

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("AC-3: a hidden column is stored, and read back by the next page", () => {
  const { result } = renderHook(() => useHiddenColumns());
  act(() => {
    result.current.toggleColumn("romaji");
  });

  expect([...storedHiddenColumns()]).toEqual(["romaji"]);
  expect([
    ...renderHook(() => useHiddenColumns()).result.current.hidden,
  ]).toEqual(["romaji"]);
});

test("an odd stored value hides nothing it does not know", () => {
  window.localStorage.setItem(
    "lyrx-hidden-columns",
    '["english", "original", 3]',
  );
  expect([...storedHiddenColumns()]).toEqual(["english"]);
  window.localStorage.setItem("lyrx-hidden-columns", "{not json");
  expect(storedHiddenColumns().size).toBe(0);
});

test("AC-3: when storage throws, columns still hide for this page", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  const { result } = renderHook(() => useHiddenColumns());

  act(() => {
    result.current.toggleColumn("english");
  });

  expect(result.current.hidden.has("english")).toBe(true);
});

test("hiding or showing a column covers again only the cells revealed in it", () => {
  const { result } = renderHook(() => useHiddenColumns());
  act(() => {
    result.current.revealCell("romaji", 1);
    result.current.revealCell("english", 1);
  });
  act(() => {
    result.current.toggleColumn("romaji");
  });

  expect([...result.current.revealed]).toEqual([cellKey("english", 1)]);
});
