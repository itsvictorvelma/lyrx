// The four versions as a table: one row per lyric line, a gap between verses, the sung, next, and looped lines marked.
import { cellKey } from "./hiddenColumns";
import { LoopIcon } from "./PlayerControls";
import type { Line, VersionColumn } from "./types";

export const NOT_AVAILABLE_TEXT = "Not available";
export const SHOW_TEXT = "Show";
export const LOOPING_TEXT = "Looping";

// How a covered cell's button names its column to a screen reader.
const COLUMN_NAMES: Record<VersionColumn, string> = {
  hiragana: "hiragana",
  romaji: "romaji",
  english: "English",
};

interface VersionsTableProps {
  lines: Line[];
  // The line being sung, highlighted; null when nothing is playing. The song page keeps it in view.
  currentLine?: number | null;
  // Clicking a timed line's original text jumps the audio to it.
  onSeek?: (line: Line) => void;
  // The column a phone shows next to the original; wider screens show all four.
  phoneColumn?: VersionColumn;
  // Covered columns, and the cells in them the learner revealed (keys from `cellKey`).
  hidden?: Set<VersionColumn>;
  revealed?: Set<string>;
  onReveal?: (column: VersionColumn, lineIndex: number) => void;
  // The line being looped, marked with an icon; null when nothing loops.
  loopLine?: number | null;
}

export function VersionsTable({
  lines,
  currentLine = null,
  onSeek,
  phoneColumn = "hiragana",
  hidden = new Set(),
  revealed = new Set(),
  onReveal,
  loopLine = null,
}: VersionsTableProps) {
  const nextLine = nextLineAfter(lines, currentLine);

  // A version's cell: its text, or a Show button while its column is covered.
  function versionCell(line: Line, column: VersionColumn) {
    const covered =
      hidden.has(column) && !revealed.has(cellKey(column, line.index));
    if (!covered) {
      return <VersionCell text={line[column]} />;
    }
    return (
      <button
        type="button"
        className="show-button"
        aria-label={`Show ${COLUMN_NAMES[column]} for: ${line.original}`}
        onClick={() => {
          onReveal?.(column, line.index);
        }}
      >
        {SHOW_TEXT}
      </button>
    );
  }

  return (
    <table className="versions-table" data-phone-column={phoneColumn}>
      <thead>
        <tr>
          <th scope="col" className="col-original">
            Original
          </th>
          <th scope="col" className="col-hiragana">
            Hiragana
          </th>
          <th scope="col" className="col-romaji">
            Romaji
          </th>
          <th scope="col" className="col-english">
            English
          </th>
        </tr>
      </thead>
      {splitIntoVerses(lines).map((verse) => (
        <tbody key={verse[0]?.index}>
          {verse.map((line) => (
            <tr
              key={line.index}
              className={rowClass(line.index, currentLine, nextLine, loopLine)}
              aria-current={line.index === currentLine ? "true" : undefined}
            >
              <td lang="ja" className="col-original">
                {onSeek !== undefined && line.startMs !== null ? (
                  <button
                    type="button"
                    className="seek-button"
                    aria-label={`Play from: ${line.original}`}
                    onClick={() => {
                      onSeek(line);
                    }}
                  >
                    {line.original}
                  </button>
                ) : (
                  line.original
                )}
                {line.index === loopLine && <LoopMark />}
              </td>
              <td lang="ja" className="col-hiragana">
                {versionCell(line, "hiragana")}
              </td>
              <td className="col-romaji">{versionCell(line, "romaji")}</td>
              <td className="col-english">{versionCell(line, "english")}</td>
            </tr>
          ))}
        </tbody>
      ))}
    </table>
  );
}

// "current" for the sung line, "next" for the one after it, "looped" for the looped one; the CSS draws the marks.
function rowClass(
  index: number,
  currentLine: number | null,
  nextLine: number | null,
  loopLine: number | null,
): string | undefined {
  const classes = [
    index === currentLine && "current",
    index === nextLine && index !== currentLine && "next",
    index === loopLine && "looped",
  ].filter(Boolean);
  return classes.length > 0 ? classes.join(" ") : undefined;
}

// The looped line's mark: an icon with a name, so it is not shown by colour alone.
function LoopMark() {
  return (
    <span className="loop-mark" role="img" aria-label={LOOPING_TEXT}>
      <LoopIcon />
    </span>
  );
}

// The first line with text after the sung one, across a verse gap; null when nothing is sung.
function nextLineAfter(
  lines: Line[],
  currentLine: number | null,
): number | null {
  if (currentLine === null) {
    return null;
  }
  const next = lines.find(
    (line) => line.index > currentLine && line.original !== "",
  );
  return next?.index ?? null;
}

// A lyric line the translator could not do comes back with empty versions; say so in words.
function VersionCell({ text }: { text: string }) {
  return text === "" ? <span className="dim">{NOT_AVAILABLE_TEXT}</span> : text;
}

// Blank lines end a verse; each verse becomes its own table body, spaced apart by CSS.
function splitIntoVerses(lines: Line[]): Line[][] {
  const verses: Line[][] = [[]];
  for (const line of lines) {
    if (line.original === "") {
      verses.push([]);
    } else {
      verses[verses.length - 1]?.push(line);
    }
  }
  return verses.filter((verse) => verse.length > 0);
}
