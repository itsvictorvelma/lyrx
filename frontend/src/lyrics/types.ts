// Data shapes the page shares with the server: one line of the four versions and the request result.

export interface Line {
  index: number;
  original: string;
  hiragana: string;
  romaji: string;
  english: string;
  readingVerified: boolean;
}

// The server error codes that have their own message on the page.
export type PageErrorCode =
  | "empty_input"
  | "no_japanese"
  | "input_too_large"
  | "model_refused"
  | "model_output_truncated"
  | "model_output_invalid"
  | "model_unavailable"
  | "server_not_configured";

export type FourVersionsResult =
  | { kind: "lines"; lines: Line[] }
  | { kind: "error"; code: string }
  // A reply arrived but was not a shape the page can trust.
  | { kind: "unreadable" }
  | { kind: "unreachable" };
