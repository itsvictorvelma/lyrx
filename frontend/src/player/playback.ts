// Playback rules without any player: a YouTube link to its video id, the line being sung, the sync,
// looping a line, and the remembered volume.
import { MAX_OFFSET_MS, VIDEO_ID } from "../api";
import { readSetting, storeSetting } from "../browser";
import type { Line } from "../types";

const OFFSET_STEP_MS = 250;
const YOUTUBE_HOSTS = new Set(["youtube.com", "music.youtube.com"]);

// The 11-character video id from a YouTube link, or null for anything else.
export function parseVideoId(link: string): string | null {
  let url: URL;
  try {
    url = new URL(link.trim());
  } catch {
    return null;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    return null;
  }
  const host = url.hostname.replace(/^(www|m)\./, "");
  const id =
    host === "youtu.be"
      ? url.pathname.split("/")[1]
      : YOUTUBE_HOSTS.has(host) && url.pathname === "/watch"
        ? url.searchParams.get("v")
        : YOUTUBE_HOSTS.has(host) && url.pathname.startsWith("/shorts/")
          ? url.pathname.split("/")[2]
          : null;
  return id !== null && id !== undefined && VIDEO_ID.test(id) ? id : null;
}

// A line counts as sung this long before its start time, so the eyes arrive in time.
// ponytail: two lines starting less than this apart can't both be landed on by Previous; rare in songs.
export const LEAD_IN_MS = 300;

// The index of the line being sung: the last line whose start plus the offset has passed.
export function currentLineIndex(
  lines: Line[],
  timeMs: number,
  offsetMs: number,
): number | null {
  let current: number | null = null;
  for (const line of lines) {
    if (line.startMs !== null && line.startMs + offsetMs <= timeMs) {
      current = line.index;
    }
  }
  return current;
}

// The offset moved by one step, kept within the limit.
export function nudgeOffset(offsetMs: number, direction: 1 | -1): number {
  const moved = offsetMs + direction * OFFSET_STEP_MS;
  return Math.max(-MAX_OFFSET_MS, Math.min(MAX_OFFSET_MS, moved));
}

// "+0.50 s" or "−0.25 s".
export function formatOffset(offsetMs: number): string {
  const sign = offsetMs < 0 ? "−" : "+";
  return `${sign}${(Math.abs(offsetMs) / 1000).toFixed(2)} s`;
}

export function hasTimings(lines: Line[]): boolean {
  return lines.some((line) => line.startMs !== null);
}

// What the page needs from any player: where it is, how long it is, and the controls.
export interface AudioClock {
  timeMs: () => number | null;
  durationMs: () => number | null;
  isPlaying: () => boolean;
  play: () => void;
  pause: () => void;
  seekMs: (milliseconds: number) => void;
  // 0 (silent) to 100 (full).
  setVolume: (percent: number) => void;
  // 1 is normal speed; 0.5 is half.
  setPlaybackRate: (rate: number) => void;
}

// The speeds the speed button steps through, in order; a press after the last starts again.
const PLAYBACK_SPEEDS = [1, 0.75, 0.5];

export function nextSpeed(speed: number): number {
  const at = PLAYBACK_SPEEDS.indexOf(speed);
  return PLAYBACK_SPEEDS[(at + 1) % PLAYBACK_SPEEDS.length] ?? 1;
}

// A YouTube search for the song, opened in a new tab; the server fetches nothing.
export function youTubeSearchUrl(track: string, artist: string): string {
  const query = encodeURIComponent(`${track} ${artist}`.trim());
  return `https://www.youtube.com/results?search_query=${query}`;
}

// "1:05" for 65,400 milliseconds.
export function formatClock(milliseconds: number): string {
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  return `${String(Math.floor(seconds / 60))}:${String(seconds % 60).padStart(2, "0")}`;
}

// Looping one line: where the loop starts and ends in the audio.

// Audio times in milliseconds, with the sync offset already applied.
interface LoopRange {
  startMs: number;
  endMs: number;
}

// From the line's start to the next timed line's start, or to the song's end for the last line.
// Null when the line has no timing.
export function loopRange(
  lines: Line[],
  lineIndex: number,
  offsetMs: number,
  durationMs: number | null,
): LoopRange | null {
  const line = lines.find((candidate) => candidate.index === lineIndex);
  if (line?.startMs === null || line?.startMs === undefined) {
    return null;
  }
  const next = lines.find(
    (candidate) => candidate.index > lineIndex && candidate.startMs !== null,
  );
  const endMs =
    next?.startMs !== null && next?.startMs !== undefined
      ? next.startMs + offsetMs
      : (durationMs ?? Number.POSITIVE_INFINITY);
  return { startMs: line.startMs + offsetMs, endMs };
}

// The player volume: 0 to 100, remembered on this browser, and what Mute and Unmute change it to.
export const VOLUME_STEP = 5;
const FULL_VOLUME = 100;
const VOLUME_STORAGE_KEY = "subbed-volume";

function isVolume(value: number): boolean {
  return Number.isInteger(value) && value >= 0 && value <= FULL_VOLUME;
}

// The remembered level; full volume when none is stored, it is broken, or storage is blocked.
export function storedVolume(): number {
  const stored = readSetting(VOLUME_STORAGE_KEY);
  const value = stored === null || stored === "" ? NaN : Number(stored);
  return isVolume(value) ? value : FULL_VOLUME;
}

export function storeVolume(volume: number): void {
  storeSetting(VOLUME_STORAGE_KEY, String(volume));
}

// Mute goes to 0; Unmute goes back to the level before, or full volume if there was none.
export function toggledVolume(volume: number, beforeMute: number): number {
  if (volume > 0) {
    return 0;
  }
  return beforeMute > 0 ? beforeMute : FULL_VOLUME;
}
