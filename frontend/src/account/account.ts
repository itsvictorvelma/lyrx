// Who is signed in, shared with every page through React context.
import { createContext, useContext } from "react";
import type { Account } from "./types";

// Before the server answers, nobody is known to be signed in or a guest.
export const UNKNOWN_ACCOUNT: Account = { username: null, checked: false };

export const AccountContext = createContext<Account>(UNKNOWN_ACCOUNT);

export function useAccount(): Account {
  return useContext(AccountContext);
}

// A guest for sure: the server said nobody is signed in.
export function isGuest(account: Account): boolean {
  return account.checked && account.username === null;
}
