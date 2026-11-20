// Playback rules without any player: a YouTube link to its video id, the line being sung, the sync.
import type { Line } from "./types";

const OFFSET_STEP_MS = 250;
export const MAX_OFFSET_MS = 30_000;
export const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
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
