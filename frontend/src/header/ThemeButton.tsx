// The sun/moon button: dark or light, remembered on this browser, else the system setting.
import { useEffect, useState } from "react";
import { matchesMedia } from "../browser";

type Theme = "dark" | "light";

const STORAGE_KEY = "lyrx-theme";

// The remembered choice, or null when none is stored or storage is blocked.
function storedTheme(): Theme | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === "dark" || value === "light" ? value : null;
  } catch {
    return null;
  }
}

function storeTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Storage blocked (private window): the choice lasts until the page closes.
  }
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
    storeTheme(next);
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

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  );
}
