// Decorative kana falling behind the loading steps, in the theme's colours; still under reduced motion.
import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "../mediaQuery";

const KANA =
  "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン" +
  "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん";
// Short everyday words a learner may catch as one column spells them out.
const RAIN_WORDS = [
  "うた",
  "こえ",
  "よる",
  "ほし",
  "そら",
  "ゆめ",
  "かぜ",
  "はな",
];

const FRAME_MS = 50; // about 20 frames a second
const WORD_EVERY_MS = 3000;
const FONT_PX = 18;
const PHONE_FONT_PX = 22;
const PHONE_WIDTH_PX = 720;
// How much of the background is painted over each frame: higher means shorter trails.
const TRAIL_FADE = 0.12;
const SLOWEST_ROWS_PER_FRAME = 0.35;
const FASTEST_ROWS_PER_FRAME = 1;
// The still field's characters are drawn this faint, and in this share of its cells.
const STILL_ALPHA = 0.25;
const STILL_DENSITY = 0.5;

export interface RainColors {
  accent: string;
  background: string;
}

interface Column {
  row: number;
  speed: number;
  // The word this column is spelling, and how many of its characters are drawn.
  word: string | null;
  spelled: number;
}

// Everything one running rain needs: its canvas, colours, columns, and timing.
interface Rain {
  canvas: HTMLCanvasElement;
  context: CanvasRenderingContext2D;
  still: boolean;
  fontFamily: string;
  colors: RainColors;
  fontPx: number;
  rows: number;
  columns: Column[];
  lastDrawnMs: number;
  lastWordMs: number;
}

// The current theme's colours, read from the CSS tokens on <html>.
export function readRainColors(): RainColors {
  const style = getComputedStyle(document.documentElement);
  return {
    accent: style.getPropertyValue("--accent").trim(),
    background: style.getPropertyValue("--bg").trim(),
  };
}

export function KanaRain() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d") ?? null;
    return canvas === null || context === null
      ? undefined
      : startRain(canvas, context);
  }, []);

  return <canvas ref={canvasRef} className="kana-rain" aria-hidden="true" />;
}

// Starts the rain; returns the function that stops it and lets go of every listener.
function startRain(
  canvas: HTMLCanvasElement,
  context: CanvasRenderingContext2D,
): () => void {
  const rain: Rain = {
    canvas,
    context,
    still: prefersReducedMotion(),
    // The page's font stack (it covers kana), inherited by the canvas from styles.css.
    fontFamily: getComputedStyle(canvas).fontFamily || "sans-serif",
    colors: readRainColors(),
    fontPx: FONT_PX,
    rows: 0,
    columns: [],
    lastDrawnMs: 0,
    lastWordMs: 0,
  };
  sizeCanvas(rain);
  const stopWatchingSize = watchSize(rain);
  const stopWatchingTheme = watchTheme(rain);
  let frame = 0;
  function loop(nowMs: number) {
    if (nowMs - rain.lastDrawnMs >= FRAME_MS) {
      rain.lastDrawnMs = nowMs;
      drawFrame(rain, nowMs);
    }
    frame = window.requestAnimationFrame(loop);
  }
  if (!rain.still) {
    frame = window.requestAnimationFrame(loop);
  }
  return () => {
    window.cancelAnimationFrame(frame);
    stopWatchingSize();
    stopWatchingTheme();
  };
}

// Matches the canvas to its box and the screen's pixel density, then starts the field over.
function sizeCanvas(rain: Rain) {
  const ratio = window.devicePixelRatio || 1;
  const width = rain.canvas.clientWidth;
  const height = rain.canvas.clientHeight;
  rain.canvas.width = Math.round(width * ratio);
  rain.canvas.height = Math.round(height * ratio);
  rain.context.setTransform(ratio, 0, 0, ratio, 0, 0);
  rain.fontPx = width < PHONE_WIDTH_PX ? PHONE_FONT_PX : FONT_PX;
  rain.rows = Math.ceil(height / rain.fontPx);
  // Spread down the screen, so the rain is there from the first frame.
  rain.columns = Array.from({ length: Math.ceil(width / rain.fontPx) }, () =>
    newColumn(Math.floor(Math.random() * rain.rows)),
  );
  repaint(rain);
}

// Resizes with the loading area, not only the window (the header can wrap, for example).
function watchSize(rain: Rain): () => void {
  if (typeof ResizeObserver !== "function") {
    return () => undefined;
  }
  const observer = new ResizeObserver(() => {
    sizeCanvas(rain);
  });
  observer.observe(rain.canvas);
  return () => {
    observer.disconnect();
  };
}

// Takes the new colours when the theme button or the system setting changes the theme.
function watchTheme(rain: Rain): () => void {
  function refreshColors() {
    rain.colors = readRainColors();
    repaint(rain);
  }
  const themeButton = new MutationObserver(refreshColors);
  themeButton.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  const system =
    typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-color-scheme: light)")
      : null;
  system?.addEventListener("change", refreshColors);
  return () => {
    themeButton.disconnect();
    system?.removeEventListener("change", refreshColors);
  };
}

// A clean background, plus the still field under reduced motion.
function repaint(rain: Rain) {
  fillBackground(rain, 1);
  if (rain.still) {
    drawStill(rain);
  }
}

function fillBackground(rain: Rain, alpha: number) {
  const { context, canvas } = rain;
  context.globalAlpha = alpha;
  context.fillStyle = rain.colors.background;
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.globalAlpha = 1;
}

function drawStill(rain: Rain) {
  const { context, fontPx } = rain;
  context.font = `${String(fontPx)}px ${rain.fontFamily}`;
  context.fillStyle = rain.colors.accent;
  context.globalAlpha = STILL_ALPHA;
  rain.columns.forEach((_, column) => {
    for (let row = 1; row <= rain.rows; row += 1) {
      if (Math.random() < STILL_DENSITY) {
        context.fillText(randomKana(), column * fontPx, row * fontPx);
      }
    }
  });
  context.globalAlpha = 1;
}

// One step of the rain: fade what is there, move every column, maybe start a word.
function drawFrame(rain: Rain, nowMs: number) {
  fillBackground(rain, TRAIL_FADE);
  rain.context.font = `${String(rain.fontPx)}px ${rain.fontFamily}`;
  rain.context.fillStyle = rain.colors.accent;
  rain.context.shadowColor = rain.colors.accent;
  rain.columns.forEach((column, index) => {
    moveColumn(rain, column, index);
  });
  rain.context.shadowBlur = 0;
  if (nowMs - rain.lastWordMs >= WORD_EVERY_MS) {
    rain.lastWordMs = nowMs;
    giveWordToAColumn(rain);
  }
}

// Moves the column down; draws a character each time it reaches a new row.
function moveColumn(rain: Rain, column: Column, index: number) {
  const before = Math.floor(column.row);
  column.row += column.speed;
  const row = Math.floor(column.row);
  if (row === before || row < 1) {
    return;
  }
  // A spelled word glows, so it stands out from the rain around it.
  rain.context.shadowBlur = column.word === null ? 0 : rain.fontPx / 2;
  rain.context.fillText(
    nextCharacter(column),
    index * rain.fontPx,
    row * rain.fontPx,
  );
  if (column.row > rain.rows) {
    Object.assign(column, newColumn(0));
  }
}

// A column in the top half of the screen spells one of the words next.
function giveWordToAColumn(rain: Rain) {
  const column = rain.columns[Math.floor(Math.random() * rain.columns.length)];
  if (column !== undefined && column.row < rain.rows / 2) {
    column.word =
      RAIN_WORDS[Math.floor(Math.random() * RAIN_WORDS.length)] ?? null;
    column.spelled = 0;
  }
}

// A column whose next character lands on `row`.
function newColumn(row: number): Column {
  return {
    row,
    speed:
      SLOWEST_ROWS_PER_FRAME +
      Math.random() * (FASTEST_ROWS_PER_FRAME - SLOWEST_ROWS_PER_FRAME),
    word: null,
    spelled: 0,
  };
}

function randomKana(): string {
  return KANA[Math.floor(Math.random() * KANA.length)] ?? "あ";
}

// The column's next character: the next letter of its word, else a random kana.
function nextCharacter(column: Column): string {
  if (column.word === null) {
    return randomKana();
  }
  const character = column.word[column.spelled] ?? randomKana();
  column.spelled += 1;
  if (column.spelled >= column.word.length) {
    column.word = null;
  }
  return character;
}
