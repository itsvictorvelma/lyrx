// The four versions as a table: one row per lyric line, a gap between verses, the sung line marked.
import { useEffect, useRef } from "react";
import type { Line } from "./types";

export const NOT_AVAILABLE_TEXT = "Not available";

interface VersionsTableProps {
  lines: Line[];
  // The line being sung, highlighted and kept in view; null when nothing is playing.
  currentLine?: number | null;
  // Clicking a timed line's original text jumps the audio to it.
  onSeek?: (line: Line) => void;
}

export function VersionsTable({
  lines,
  currentLine = null,
  onSeek,
}: VersionsTableProps) {
  const currentRow = useRef<HTMLTableRowElement>(null);

  useEffect(() => {
    const row = currentRow.current;
    // jsdom (the test browser) has neither scrollIntoView nor matchMedia, so both are checked.
    if (currentLine === null || row === null || !("scrollIntoView" in row)) {
      return;
    }
    const reduceMotion =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    row.scrollIntoView({
      block: "nearest",
      behavior: reduceMotion ? "auto" : "smooth",
    });
  }, [currentLine]);

  return (
    <div className="table-scroll">
      <table className="versions-table">
        <thead>
          <tr>
            <th scope="col">Original</th>
            <th scope="col">Hiragana</th>
            <th scope="col">Romaji</th>
            <th scope="col">English</th>
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
                <td lang="ja">
                  {onSeek !== undefined && line.startMs !== null ? (
                    <button
                      type="button"
                      className="link-button seek-button"
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
                <td lang="ja">
                  <VersionCell text={line.hiragana} />
                </td>
                <td>
                  <VersionCell text={line.romaji} />
                </td>
                <td>
                  <VersionCell text={line.english} />
                </td>
              </tr>
            ))}
          </tbody>
        ))}
      </table>
    </div>
  );
}

// A lyric line the translator could not do comes back with empty versions; say so in words.
function VersionCell({ text }: { text: string }) {
  return text === "" ? (
    <span className="muted">{NOT_AVAILABLE_TEXT}</span>
  ) : (
    text
  );
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
