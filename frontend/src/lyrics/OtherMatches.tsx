// "Not this one?": a popover of the other search results; each opens that song instead.
import type { SearchResult } from "./types";

interface OtherMatchesProps {
  results: SearchResult[];
  onPick: (result: SearchResult) => void;
}

export function OtherMatches({ results, onPick }: OtherMatchesProps) {
  if (results.length === 0) {
    return null;
  }
  return (
    <details className="other-matches">
      <summary className="pill-button">Not this one?</summary>
      <ul className="popover">
        {results.map((result) => (
          <li key={result.id}>
            <button
              type="button"
              className="match-button"
              onClick={() => {
                onPick(result);
              }}
            >
              {result.track} — {result.artist},{" "}
              {formatDuration(result.durationSeconds)}
            </button>
            {result.looksJapanese ? null : (
              <span className="dim"> Not Japanese</span>
            )}
            {result.saved ? <span className="dim"> Saved</span> : null}
          </li>
        ))}
      </ul>
    </details>
  );
}

// 214 seconds is "3:34".
export function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes)}:${String(rest).padStart(2, "0")}`;
}
