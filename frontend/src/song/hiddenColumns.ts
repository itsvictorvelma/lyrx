// Which versions are covered for self-testing (remembered on this browser), and which covered cells are revealed.
import { useState } from "react";
import { readSetting, storeSetting } from "../browser";
import type { VersionColumn } from "../types";

const STORAGE_KEY = "subbed-hidden-columns";
const COLUMNS: VersionColumn[] = ["hiragana", "romaji", "english"];

// The remembered hidden columns; none when nothing is stored, the value is odd, or storage is blocked.
export function storedHiddenColumns(): Set<VersionColumn> {
  try {
    const parsed: unknown = JSON.parse(readSetting(STORAGE_KEY) ?? "[]");
    const list: unknown[] = Array.isArray(parsed) ? parsed : [];
    return new Set(COLUMNS.filter((column) => list.includes(column)));
  } catch {
    return new Set();
  }
}

// One covered cell, as "romaji:3".
export function cellKey(column: VersionColumn, lineIndex: number): string {
  return `${column}:${String(lineIndex)}`;
}

export function useHiddenColumns() {
  const [hidden, setHidden] = useState(storedHiddenColumns);
  const [revealed, setRevealed] = useState<Set<string>>(() => new Set());

  // Hiding or showing a column also covers again the cells revealed in it.
  function toggleColumn(column: VersionColumn) {
    const next = new Set(hidden);
    if (next.has(column)) {
      next.delete(column);
    } else {
      next.add(column);
    }
    setHidden(next);
    storeSetting(STORAGE_KEY, JSON.stringify([...next]));
    setRevealed(
      (previous) =>
        new Set([...previous].filter((key) => !key.startsWith(`${column}:`))),
    );
  }

  function revealCell(column: VersionColumn, lineIndex: number) {
    setRevealed((previous) =>
      new Set(previous).add(cellKey(column, lineIndex)),
    );
  }

  return { hidden, revealed, toggleColumn, revealCell };
}
