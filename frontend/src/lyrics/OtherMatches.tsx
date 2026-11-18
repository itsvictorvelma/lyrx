// "Not this song?": the other search results as buttons that open that song instead.
import type { SearchResult } from "./types";

interface OtherMatchesProps {
  results: SearchResult[];
  busy: boolean;
  onPick: (result: SearchResult) => void;
}

export function OtherMatches({ results, busy, onPick }: OtherMatchesProps) {
  if (results.length === 0) {
    return null;
  }
  return (
    <details className="other-matches">
      <summary>Not this song?</summary>
      <ul>
        {results.map((result) => (
          <li key={result.id}>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                onPick(result);
              }}
            >
              {result.track} — {result.artist},{" "}
              {formatDuration(result.durationSeconds)}
            </button>
            {result.looksJapanese ? null : (
              <span className="muted"> Not Japanese</span>
            )}
            {result.saved ? <span className="muted"> Saved</span> : null}
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
