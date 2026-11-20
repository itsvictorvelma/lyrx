// The home page's example line: its parts, and which part is sung at each tick of the animation.

// An invented line, never real lyrics: "I wait for you in the town at dawn".
export const HERO_PARTS = [
  { original: "夜明けの", hiragana: "よあけ の", romaji: "yoake no" },
  { original: "街で", hiragana: "まち で", romaji: "machi de" },
  { original: "君を", hiragana: "きみ を", romaji: "kimi wo" },
  { original: "待つ", hiragana: "まつ", romaji: "matsu" },
];
export const HERO_ENGLISH = "I wait for you in the town at dawn";
export const HERO_LABEL = `Example line: ${HERO_PARTS.map((part) => part.original).join("")}, ${HERO_ENGLISH}`;

export const HERO_TICK_MS = 650;
// One tick per part, one for the English, then a pause with the whole line shown.
const PAUSE_TICKS = 4;
const TICKS_PER_LOOP = HERO_PARTS.length + 1 + PAUSE_TICKS;
const LOOPS = 3;
// After the last loop the line rests, fully shown, so it never moves forever.
export const HERO_LAST_TICK = TICKS_PER_LOOP * LOOPS;

export type PartState = "waiting" | "current" | "sung";

// How far the line is at a tick: 0 before the first part, then 1 per part, then the whole line.
function progressAt(tick: number): number {
  if (tick >= HERO_LAST_TICK) {
    return HERO_PARTS.length + 1;
  }
  return tick % TICKS_PER_LOOP;
}

export function partStateAt(tick: number, partIndex: number): PartState {
  const progress = progressAt(tick);
  if (progress > HERO_PARTS.length || partIndex < progress - 1) {
    return "sung";
  }
  return partIndex === progress - 1 ? "current" : "waiting";
}

export function englishShownAt(tick: number): boolean {
  return progressAt(tick) > HERO_PARTS.length;
}
