// The four versions as a table: one row per lyric line, a gap between verses instead of blank rows.
import type { Line } from "./types";

export const NOT_AVAILABLE_TEXT = "Not available";

interface VersionsTableProps {
  lines: Line[];
}

export function VersionsTable({ lines }: VersionsTableProps) {
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
              <tr key={line.index}>
                <td lang="ja">{line.original}</td>
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

// A lyric line Gemini could not do comes back with empty versions; say so in words.
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
