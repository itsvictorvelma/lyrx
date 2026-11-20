// Calls the Lyrx server (search, open a song, saved and recent songs, playback) and checks replies.
import { MAX_OFFSET_MS, VIDEO_ID } from "./player/playback";
import type {
  ApiResult,
  Line,
  Playback,
  RecentSong,
  SavedSong,
  SearchResult,
  Song,
  SongVersions,
} from "./types";

export async function searchSongs(
  query: string,
): Promise<ApiResult<SearchResult[]>> {
  const result = await requestJson(
    "POST",
    "/api/song-search",
    { query },
    isSearchReply,
  );
  return result.kind === "ok"
    ? { kind: "ok", value: result.value.results }
    : result;
}

export function getSongVersions(id: number): Promise<ApiResult<SongVersions>> {
  return requestJson("POST", "/api/song-versions", { id }, isSongVersionsReply);
}

export async function listSavedSongs(): Promise<ApiResult<SavedSong[]>> {
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

// Songs anyone opened lately, newest first, for the home page row.
export async function listRecentSongs(): Promise<ApiResult<RecentSong[]>> {
  const result = await requestJson(
    "GET",
    "/api/recent-songs",
    undefined,
    isRecentSongsReply,
  );
  return result.kind === "ok"
    ? { kind: "ok", value: result.value.songs }
    : result;
}

// Puts a song the server has opened in the library, with its video and sync.
export function saveSong(
  id: number,
  playback: Playback,
): Promise<ApiResult<null>> {
  return requestJson(
    "PUT",
    `/api/songs/${String(id)}/saved`,
    playback,
    isNull,
    204,
  );
}

// Takes a song out of the library; the server still keeps its translation.
export function unsaveSong(id: number): Promise<ApiResult<null>> {
  return requestJson(
    "DELETE",
    `/api/songs/${String(id)}/saved`,
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

// The reply of `GET /api/account`, sign-up, and sign-in.
interface AccountReply {
  username: string | null;
}

function isAccountReply(value: unknown): value is AccountReply {
  return (
    isRecord(value) &&
    (value.username === null || typeof value.username === "string")
  );
}

// The signed-in username, or null for a guest.
export async function getAccount(): Promise<ApiResult<string | null>> {
  const result = await requestJson(
    "GET",
    "/api/account",
    undefined,
    isAccountReply,
  );
  return result.kind === "ok"
    ? { kind: "ok", value: result.value.username }
    : result;
}

export type AccountMode = "sign-in" | "sign-up";

// Signs in, or creates the account and signs it in; the reply is the stored username.
export async function enterAccount(
  mode: AccountMode,
  username: string,
  password: string,
): Promise<ApiResult<string>> {
  const result = await requestJson(
    "POST",
    `/api/account/${mode}`,
    { username, password },
    isAccountReply,
  );
  if (result.kind !== "ok") {
    return result;
  }
  return result.value.username === null
    ? { kind: "unreadable" }
    : { kind: "ok", value: result.value.username };
}

export function signOut(): Promise<ApiResult<null>> {
  return requestJson("POST", "/api/account/sign-out", undefined, isNull, 204);
}

// Deletes the account and its saved songs; the password is asked again.
export function deleteAccount(password: string): Promise<ApiResult<null>> {
  return requestJson("DELETE", "/api/account", { password }, isNull, 204);
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
  // Only a 204 has no body; an error reply always carries its code and message.
  const reply = response.status === 204 ? null : parseJson(text);
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

function isVideoIdOrNull(value: unknown): value is string | null {
  return value === null || (typeof value === "string" && VIDEO_ID.test(value));
}

function isPlayback(value: unknown): value is Playback {
  return (
    isRecord(value) &&
    isVideoIdOrNull(value.videoId) &&
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

function isSavedSong(value: unknown): value is SavedSong {
  return (
    isRecord(value) &&
    isSong(value) &&
    isPlayback(value) &&
    Number.isInteger(value.lastOpenedAt)
  );
}

function isRecentSong(value: unknown): value is RecentSong {
  return isRecord(value) && isSong(value) && isVideoIdOrNull(value.videoId);
}

function isRecentSongsReply(value: unknown): value is { songs: RecentSong[] } {
  return (
    isRecord(value) &&
    Array.isArray(value.songs) &&
    value.songs.every(isRecentSong)
  );
}

function isSavedSongsReply(value: unknown): value is { songs: SavedSong[] } {
  return (
    isRecord(value) &&
    Array.isArray(value.songs) &&
    value.songs.every(isSavedSong)
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
    typeof value.saved === "boolean" &&
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

export const FALLBACK_MESSAGE = "Something went wrong. Try again.";
const SERVER_UNREACHABLE_MESSAGE =
  "Could not reach the Lyrx server. Is it running?";

// What the page says about a failed request: the server's own message when it sent one.
export function errorMessage(
  result: Exclude<ApiResult<unknown>, { kind: "ok" }>,
): string {
  switch (result.kind) {
    case "error":
      return result.message;
    case "unreadable":
      return FALLBACK_MESSAGE;
    case "unreachable":
      return SERVER_UNREACHABLE_MESSAGE;
  }
}
