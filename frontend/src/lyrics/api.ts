// Calls the Lyrx server (search, open a song, paste) and checks every reply before use.
import type {
  ApiResult,
  Line,
  SearchResult,
  Song,
  SongVersions,
} from "./types";

export async function searchSongs(
  query: string,
): Promise<ApiResult<SearchResult[]>> {
  const result = await postJson("/api/song-search", { query }, isSearchReply);
  return result.kind === "ok"
    ? { kind: "ok", value: result.value.results }
    : result;
}

export function getSongVersions(id: number): Promise<ApiResult<SongVersions>> {
  return postJson("/api/song-versions", { id }, isSongVersionsReply);
}

export async function getPasteVersions(
  lyrics: string,
): Promise<ApiResult<Line[]>> {
  const result = await postJson("/api/versions", { lyrics }, isLinesReply);
  return result.kind === "ok"
    ? { kind: "ok", value: result.value.lines }
    : result;
}

async function postJson<Reply>(
  url: string,
  body: unknown,
  isValid: (value: unknown) => value is Reply,
): Promise<ApiResult<Reply>> {
  let response: Response;
  let text: string;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return { kind: "unreachable" };
  }
  try {
    text = await response.text();
  } catch {
    return { kind: "unreadable" };
  }
  const reply = parseJson(text);
  if (response.status === 200) {
    return isValid(reply)
      ? { kind: "ok", value: reply }
      : { kind: "unreadable" };
  }
  return isErrorReply(reply)
    ? { kind: "error", code: reply.code, message: reply.message }
    : { kind: "unreadable" };
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isLine(value: unknown): value is Line {
  return (
    isRecord(value) &&
    Number.isInteger(value.index) &&
    typeof value.original === "string" &&
    typeof value.hiragana === "string" &&
    typeof value.romaji === "string" &&
    typeof value.english === "string"
  );
}

// Indexes must run 0, 1, 2… in order with no gaps, as the server promises.
function isLineList(value: unknown): value is Line[] {
  return (
    Array.isArray(value) &&
    value.every(
      (line: unknown, position) => isLine(line) && line.index === position,
    )
  );
}

function isSong(value: unknown): value is Song {
  return (
    isRecord(value) &&
    Number.isInteger(value.id) &&
    typeof value.track === "string" &&
    typeof value.artist === "string" &&
    typeof value.album === "string" &&
    Number.isInteger(value.durationSeconds)
  );
}

function isSearchResult(value: unknown): value is SearchResult {
  return (
    isRecord(value) && isSong(value) && typeof value.looksJapanese === "boolean"
  );
}

function isSearchReply(value: unknown): value is { results: SearchResult[] } {
  return (
    isRecord(value) &&
    Array.isArray(value.results) &&
    value.results.every(isSearchResult)
  );
}

function isSongVersionsReply(value: unknown): value is SongVersions {
  return isRecord(value) && isSong(value.song) && isLineList(value.lines);
}

function isLinesReply(value: unknown): value is { lines: Line[] } {
  return isRecord(value) && isLineList(value.lines);
}

function isErrorReply(
  value: unknown,
): value is { code: string; message: string } {
  return (
    isRecord(value) &&
    typeof value.code === "string" &&
    typeof value.message === "string"
  );
}
