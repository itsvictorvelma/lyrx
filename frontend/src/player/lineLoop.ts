// Looping one line: where the loop starts and ends in the audio.
import type { Line } from "../types";

// Audio times in milliseconds, with the sync offset already applied.
export interface LoopRange {
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
