// The song page's keyboard shortcuts: which key does what, and when keys are left alone.
import { useEffect, useEffectEvent } from "react";
import type { VersionColumn } from "./types";

export type Shortcut =
  | { kind: "togglePlay" }
  | { kind: "previousLine" }
  | { kind: "nextLine" }
  | { kind: "toggleLoop" }
  | { kind: "toggleColumn"; column: VersionColumn }
  | { kind: "toggleFocus" }
  | { kind: "escape" }
  | { kind: "toggleShortcutList" };

// The list the learner sees, in the order shown.
export const SHORTCUT_LIST: { keys: string; does: string }[] = [
  { keys: "Space", does: "Play or pause" },
  { keys: "← / →", does: "Previous / next line" },
  { keys: "L", does: "Loop line on or off" },
  { keys: "H / R / E", does: "Hide or show Hiragana / Romaji / English" },
  { keys: "F", does: "Focus mode on or off" },
  { keys: "Esc", does: "Leave Focus mode" },
  { keys: "?", does: "Show or hide this list" },
];

const KEY_SHORTCUTS: Record<string, Shortcut> = {
  " ": { kind: "togglePlay" },
  ArrowLeft: { kind: "previousLine" },
  ArrowRight: { kind: "nextLine" },
  l: { kind: "toggleLoop" },
  h: { kind: "toggleColumn", column: "hiragana" },
  r: { kind: "toggleColumn", column: "romaji" },
  e: { kind: "toggleColumn", column: "english" },
  f: { kind: "toggleFocus" },
  Escape: { kind: "escape" },
  "?": { kind: "toggleShortcutList" },
};

// Where every key belongs to the control: typing, choosing, or moving the slider.
const OWNS_ALL_KEYS = "input, textarea, select, [contenteditable]";
// Where Space already presses the control.
const OWNS_SPACE = "button, a, summary";

// The shortcut for a key press, or null when the key is not one or is left to the page.
export function shortcutFor(event: KeyboardEvent): Shortcut | null {
  // A held key repeats; a shortcut fires once per press.
  if (event.repeat || event.ctrlKey || event.metaKey || event.altKey) {
    return null;
  }
  const target = event.target instanceof Element ? event.target : null;
  if (target?.closest(OWNS_ALL_KEYS)) {
    return null;
  }
  if (event.key === " " && target?.closest(OWNS_SPACE)) {
    return null;
  }
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
  return KEY_SHORTCUTS[key] ?? null;
}

// Calls `onShortcut` for every shortcut pressed anywhere on the page while it is mounted.
export function useShortcuts(onShortcut: (shortcut: Shortcut) => void): void {
  const handleKey = useEffectEvent((event: KeyboardEvent) => {
    const shortcut = shortcutFor(event);
    if (shortcut !== null) {
      event.preventDefault();
      onShortcut(shortcut);
    }
  });

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      handleKey(event);
    };
    window.addEventListener("keydown", listener);
    return () => {
      window.removeEventListener("keydown", listener);
    };
  }, []);
}
