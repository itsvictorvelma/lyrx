// Data shapes the page shares with the server: a line, a song, playback, a request result.

export interface Line {
  index: number;
  original: string;
  hiragana: string;
  romaji: string;
  english: string;
  // When the line starts in the song, in milliseconds; null when unknown or blank.
  startMs: number | null;
}

// The versions next to the original: the phone shows one of them, and any of them can be hidden.
export type VersionColumn = "hiragana" | "romaji" | "english";

// A saved song's YouTube video and how far its line timings are moved, in milliseconds.
export interface Playback {
  videoId: string | null;
  offsetMs: number;
}

// Where the audio is, as last read from the player; null before a player is ready.
export interface Progress {
  timeMs: number | null;
  durationMs: number | null;
  playing: boolean;
}

export interface Song {
  id: number;
  track: string;
  artist: string;
  album: string;
  durationSeconds: number;
}

// A saved song in the library: its video and sync, and when it was last opened (Unix milliseconds).
export interface SavedSong extends Song {
  videoId: string | null;
  offsetMs: number;
  lastOpenedAt: number;
}

// A recently opened song on the home page row: its saved video, if any, for the thumbnail.
export interface RecentSong extends Song {
  videoId: string | null;
}

export interface SearchResult extends Song {
  looksJapanese: boolean;
  saved: boolean;
}

export interface SongVersions {
  song: Song;
  lines: Line[];
  // True when the server had already translated the song (its cache), not a new translation.
  fromLibrary: boolean;
  playback: Playback;
  // Whether the song is in the learner's library.
  saved: boolean;
}

export type ApiResult<Value> =
  | { kind: "ok"; value: Value }
  | { kind: "error"; code: string; message: string }
  // A reply arrived but was not a shape the page can trust.
  | { kind: "unreadable" }
  | { kind: "unreachable" };
