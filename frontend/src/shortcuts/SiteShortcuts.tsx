// The shortcuts on every page but a song: ? for the list, / for the search box.
import { useState } from "react";
import { focusSearchBox } from "../search/SearchForm";
import { ShortcutList } from "./ShortcutList";
import { SITE_SHORTCUT_LIST, useShortcuts } from "./shortcuts";

// Off the song page only these keys are shortcuts; the rest stay with the browser.
const SITE_SHORTCUTS = ["toggleShortcutList", "escape", "focusSearch"] as const;

// Every page but a song: ? shows or hides the shortcut list, / jumps to the search box.
export function SiteShortcuts() {
  const [open, setOpen] = useState(false);

  useShortcuts((shortcut) => {
    if (shortcut.kind === "toggleShortcutList") {
      setOpen((current) => !current);
    } else if (shortcut.kind === "escape") {
      setOpen(false);
    } else if (shortcut.kind === "focusSearch") {
      focusSearchBox();
    }
  }, SITE_SHORTCUTS);

  return open ? (
    <ShortcutList
      shortcuts={SITE_SHORTCUT_LIST}
      onClose={() => {
        setOpen(false);
      }}
    />
  ) : null;
}
