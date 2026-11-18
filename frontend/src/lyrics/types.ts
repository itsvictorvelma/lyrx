// Data shapes the page shares with the server: a line, a song, a search result, a request result.

export interface Line {
  index: number;
  original: string;
  hiragana: string;
  romaji: string;
  english: string;
}

export interface Song {
  id: number;
  track: string;
  artist: string;
  album: string;
  durationSeconds: number;
}

export interface SearchResult extends Song {
  looksJapanese: boolean;
  saved: boolean;
}

export interface SongVersions {
  song: Song;
  lines: Line[];
  fromLibrary: boolean;
}

export type ApiResult<Value> =
  | { kind: "ok"; value: Value }
  | { kind: "error"; code: string; message: string }
  // A reply arrived but was not a shape the page can trust.
  | { kind: "unreadable" }
  | { kind: "unreachable" };
