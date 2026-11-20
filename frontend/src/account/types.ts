// Data shapes for accounts, shared with the server.

// Who is signed in, as the page knows it.
export interface Account {
  // The signed-in username; null for a guest, and while the first check is still running.
  username: string | null;
  // False until the server has said who is signed in.
  checked: boolean;
}

// The reply of `GET /api/account`, sign-up, and sign-in.
export interface AccountReply {
  username: string | null;
}
