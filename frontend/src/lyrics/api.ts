// Asks the Lyrx server for the four versions of pasted lyrics and checks its reply.
import type { FourVersionsResult, Line } from "./types";

const VERSIONS_URL = "/api/versions";

export async function getFourVersions(
  lyrics: string,
): Promise<FourVersionsResult> {
  let response: Response;
  try {
    response = await fetch(VERSIONS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lyrics }),
    });
  } catch {
    return { kind: "unreachable" };
  }

  let bodyText: string;
  try {
    bodyText = await response.text();
  } catch {
    return { kind: "unreadable" };
  }
  return readReply(response.status, parseJson(bodyText));
}

function readReply(status: number, body: unknown): FourVersionsResult {
  if (status === 200) {
    return isLinesReply(body)
      ? { kind: "lines", lines: body.lines }
      : { kind: "unreadable" };
  }
  if (!isErrorReply(body)) {
    return { kind: "unreadable" };
  }
  return body.details !== undefined
    ? { kind: "error", code: body.code, details: body.details }
    : { kind: "error", code: body.code };
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
    typeof value.readingVerified === "boolean"
  );
}

// Indexes must run 0, 1, 2… in order with no gaps, as the server promises.
function isLinesReply(value: unknown): value is { lines: Line[] } {
  return (
    isRecord(value) &&
    Array.isArray(value.lines) &&
    value.lines.every(
      (line: unknown, position) => isLine(line) && line.index === position,
    )
  );
}

function isErrorReply(
  value: unknown,
): value is { code: string; details?: unknown } {
  return isRecord(value) && typeof value.code === "string";
}
