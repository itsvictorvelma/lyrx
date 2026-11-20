// Who is signed in, shared with every page through React context.
import { createContext, useContext } from "react";

export interface Account {
  // The signed-in username; null for a guest, and while the first check is still running.
  username: string | null;
  // False until the server has said who is signed in.
  checked: boolean;
}

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
