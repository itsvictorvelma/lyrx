// Calls the account routes: who is signed in, sign up, sign in, sign out, delete the account.
import { isNull, isRecord, requestJson } from "../lyrics/api";
import type { ApiResult } from "../lyrics/types";

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
