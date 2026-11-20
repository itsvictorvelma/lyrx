// The sun/moon button: dark or light, remembered on this browser, else the system setting.
import { useEffect, useState } from "react";
import { matchesMedia, readSetting, storeSetting } from "../browser";
import { MoonIcon, SunIcon } from "../icons";

type Theme = "dark" | "light";

const STORAGE_KEY = "lyrx-theme";

// The remembered choice, or null when none is stored or storage is blocked.
function storedTheme(): Theme | null {
  const value = readSetting(STORAGE_KEY);
  return value === "dark" || value === "light" ? value : null;
}

function systemTheme(): Theme {
  return matchesMedia("(prefers-color-scheme: light)") ? "light" : "dark";
}

// Sets the theme on <html>, where styles.css reads it; null leaves it to the system.
function applyTheme(theme: Theme | null): void {
  if (theme === null) {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = theme;
  }
}

export function ThemeButton() {
  const [chosen, setChosen] = useState<Theme | null>(storedTheme);
  const shown = chosen ?? systemTheme();

  useEffect(() => {
    applyTheme(chosen);
  }, [chosen]);

  function toggle() {
    const next = shown === "dark" ? "light" : "dark";
    storeSetting(STORAGE_KEY, next);
    setChosen(next);
  }

  return (
    <button
      type="button"
      className="icon-button"
      aria-label={
        shown === "dark" ? "Switch to light mode" : "Switch to dark mode"
      }
      onClick={toggle}
    >
      {shown === "dark" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
