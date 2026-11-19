// The four versions as a table: one row per lyric line, a gap between verses, the sung line marked.
import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "../mediaQuery";
import type { Line } from "./types";

const NOT_AVAILABLE_TEXT = "Not available";

// The column a phone shows next to the original; wider screens show all four.
export type PhoneColumn = "hiragana" | "romaji" | "english";

interface VersionsTableProps {
  lines: Line[];
  // The line being sung, highlighted and kept in view; null when nothing is playing.
  currentLine?: number | null;
  // Clicking a timed line's original text jumps the audio to it.
  onSeek?: (line: Line) => void;
  // While audio plays, the lines not being sung are dimmed.
  playing?: boolean;
  phoneColumn?: PhoneColumn;
}

export function VersionsTable({
  lines,
  currentLine = null,
  onSeek,
  playing = false,
  phoneColumn = "hiragana",
}: VersionsTableProps) {
  const currentRow = useRef<HTMLTableRowElement>(null);

  useEffect(() => {
    const row = currentRow.current;
    // jsdom (the test browser) has no scrollIntoView, so it is checked.
    if (currentLine === null || row === null || !("scrollIntoView" in row)) {
      return;
    }
    row.scrollIntoView({
      block: "center",
      behavior: prefersReducedMotion() ? "auto" : "smooth",
    });
  }, [currentLine]);

  return (
    <table
      className={playing ? "versions-table is-playing" : "versions-table"}
      data-phone-column={phoneColumn}
    >
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
              ref={line.index === currentLine ? currentRow : undefined}
              className={line.index === currentLine ? "current" : undefined}
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
