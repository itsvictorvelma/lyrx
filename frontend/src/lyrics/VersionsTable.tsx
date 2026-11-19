// The four versions as a table: one row per lyric line, a gap between verses, the sung and next lines marked.
import type { Line } from "./types";

export const NOT_AVAILABLE_TEXT = "Not available";

// The column a phone shows next to the original; wider screens show all four.
export type PhoneColumn = "hiragana" | "romaji" | "english";

interface VersionsTableProps {
  lines: Line[];
  // The line being sung, highlighted; null when nothing is playing. The song page keeps it in view.
  currentLine?: number | null;
  // Clicking a timed line's original text jumps the audio to it.
  onSeek?: (line: Line) => void;
  phoneColumn?: PhoneColumn;
}

export function VersionsTable({
  lines,
  currentLine = null,
  onSeek,
  phoneColumn = "hiragana",
}: VersionsTableProps) {
  const nextLine = nextLineAfter(lines, currentLine);

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
              className={rowClass(line.index, currentLine, nextLine)}
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
              </td>
              <td lang="ja" className="col-hiragana">
                <VersionCell text={line.hiragana} />
              </td>
              <td className="col-romaji">
                <VersionCell text={line.romaji} />
              </td>
              <td className="col-english">
                <VersionCell text={line.english} />
              </td>
            </tr>
          ))}
        </tbody>
      ))}
    </table>
  );
}

// "current" for the sung line, "next" for the one after it; the CSS draws the marks.
function rowClass(
  index: number,
  currentLine: number | null,
  nextLine: number | null,
): string | undefined {
  if (index === currentLine) {
    return "current";
  }
  return index === nextLine ? "next" : undefined;
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
