// Calls the Lyrx server (search, open a song, saved songs, playback) and checks every reply.
import { MAX_OFFSET_MS, VIDEO_ID } from "./playback";
import type {
  ApiResult,
  Line,
  Playback,
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

export async function listSavedSongs(): Promise<ApiResult<Song[]>> {
  const result = await requestJson(
    "GET",
    "/api/songs",
    undefined,
    isSavedSongsReply,
  );
  return result.kind === "ok"
    ? { kind: "ok", value: result.value.songs }
    : result;
}

export function removeSavedSong(id: number): Promise<ApiResult<null>> {
  return requestJson(
    "DELETE",
    `/api/songs/${String(id)}`,
    undefined,
    isNull,
    204,
  );
}

// Saves a saved song's video and sync; a 404 means the song is not saved, so nothing is kept.
export function savePlayback(
  id: number,
  playback: Playback,
): Promise<ApiResult<null>> {
  return requestJson(
    "PUT",
    `/api/songs/${String(id)}/playback`,
    playback,
    isNull,
    204,
  );
}

function postJson<Reply>(
  url: string,
  body: unknown,
  isValid: (value: unknown) => value is Reply,
): Promise<ApiResult<Reply>> {
  return requestJson("POST", url, body, isValid);
}

// One request; a reply with `okStatus` must pass `isValid`, any other must be the error shape.
async function requestJson<Reply>(
  method: "GET" | "POST" | "PUT" | "DELETE",
  url: string,
  body: unknown,
  isValid: (value: unknown) => value is Reply,
  okStatus = 200,
): Promise<ApiResult<Reply>> {
  let response: Response;
  let text: string;
  try {
    response = await fetch(url, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    return { kind: "unreachable" };
  }
  try {
    text = await response.text();
  } catch {
    return { kind: "unreadable" };
  }
  const reply = okStatus === 204 ? null : parseJson(text);
  if (response.status === okStatus) {
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
    typeof value.english === "string" &&
    (value.startMs === null ||
      (Number.isInteger(value.startMs) && Number(value.startMs) >= 0))
  );
}

function isPlayback(value: unknown): value is Playback {
  return (
    isRecord(value) &&
    (value.videoId === null ||
      (typeof value.videoId === "string" && VIDEO_ID.test(value.videoId))) &&
    Number.isInteger(value.offsetMs) &&
    Math.abs(Number(value.offsetMs)) <= MAX_OFFSET_MS
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
    isRecord(value) &&
    isSong(value) &&
    typeof value.looksJapanese === "boolean" &&
    typeof value.saved === "boolean"
  );
}

function isSavedSongsReply(value: unknown): value is { songs: Song[] } {
  return (
    isRecord(value) && Array.isArray(value.songs) && value.songs.every(isSong)
  );
}

function isNull(value: unknown): value is null {
  return value === null;
}

function isSearchReply(value: unknown): value is { results: SearchResult[] } {
  return (
    isRecord(value) &&
    Array.isArray(value.results) &&
    value.results.every(isSearchResult)
  );
}

function isSongVersionsReply(value: unknown): value is SongVersions {
  return (
    isRecord(value) &&
    isSong(value.song) &&
    isLineList(value.lines) &&
    typeof value.fromLibrary === "boolean" &&
    isPlayback(value.playback)
  );
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
