// Playback rules without any player: a YouTube link to its video id, the line being sung, the sync.
import type { Line } from "./types";

export const OFFSET_STEP_MS = 250;
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

// What the page needs from any player: where it is now, and a way to jump.
export interface AudioClock {
  timeMs: () => number | null;
  seekMs: (milliseconds: number) => void;
}
