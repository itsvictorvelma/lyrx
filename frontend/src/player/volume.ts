// The player volume: 0 to 100, remembered on this browser, and what Mute and Unmute change it to.

export const VOLUME_STEP = 5;
const FULL_VOLUME = 100;
const STORAGE_KEY = "lyrx-volume";

function isVolume(value: number): boolean {
  return Number.isInteger(value) && value >= 0 && value <= FULL_VOLUME;
}

// The remembered level; full volume when none is stored, it is broken, or storage is blocked.
export function storedVolume(): number {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const value = stored === null || stored === "" ? NaN : Number(stored);
    return isVolume(value) ? value : FULL_VOLUME;
  } catch {
    return FULL_VOLUME;
  }
}

export function storeVolume(volume: number): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, String(volume));
  } catch {
    // Storage blocked (private window): the level lasts until the page closes.
  }
}

// Mute goes to 0; Unmute goes back to the level before, or full volume if there was none.
export function toggledVolume(volume: number, beforeMute: number): number {
  if (volume > 0) {
    return 0;
  }
  return beforeMute > 0 ? beforeMute : FULL_VOLUME;
}
