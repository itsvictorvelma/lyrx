// The account page (/account): sign in or create an account; when signed in, sign out or delete.
import { useState } from "react";
import type { SubmitEvent } from "react";
import type { ApiResult } from "../lyrics/types";
import { deleteAccount, enterAccount, signOut } from "./accountApi";
import type { AccountMode } from "./accountApi";
import { useAccount } from "./useAccount";

// These mirror the account rules in the server's config.py, which checks them again.
const USERNAME_MAX_CHARACTERS = 30;
const PASSWORD_MAX_CHARACTERS = 128;
export const RULES_TEXT = `Usernames are 3–${String(USERNAME_MAX_CHARACTERS)} letters, digits, _ or -. Passwords are 8–${String(PASSWORD_MAX_CHARACTERS)} characters.`;
const FALLBACK_TEXT = "Something went wrong. Try again.";
const UNREACHABLE_TEXT = "Could not reach the Lyrx server. Is it running?";

const MODES: { mode: AccountMode; label: string }[] = [
  { mode: "sign-in", label: "Sign in" },
  { mode: "sign-up", label: "Create account" },
];

interface AccountPageProps {
  onSignedIn: (username: string) => void;
  onSignedOut: () => void;
}

export function AccountPage({ onSignedIn, onSignedOut }: AccountPageProps) {
  const { username, checked } = useAccount();
  if (!checked) {
    return null;
  }
  return username === null ? (
    <SignInForm onSignedIn={onSignedIn} />
  ) : (
    <SignedIn username={username} onSignedOut={onSignedOut} />
  );
}

function errorText(result: Exclude<ApiResult<unknown>, { kind: "ok" }>) {
  if (result.kind === "error") {
    return result.code === "invalid_request" ? RULES_TEXT : result.message;
  }
  return result.kind === "unreachable" ? UNREACHABLE_TEXT : FALLBACK_TEXT;
}

function SignInForm({ onSignedIn }: { onSignedIn: (name: string) => void }) {
  const [mode, setMode] = useState<AccountMode>("sign-in");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const title = mode === "sign-in" ? "Sign in" : "Create account";

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const result = await enterAccount(mode, username.trim(), password);
    setBusy(false);
    if (result.kind === "ok") {
      onSignedIn(result.value);
    } else {
      setError(errorText(result));
    }
  }

  return (
    <section className="page account-page" aria-labelledby="account-title">
      <h1 id="account-title">{title}</h1>
      <p className="dim">Save songs and their videos to come back to them.</p>
      <div className="segmented" role="group" aria-label="Sign in or create">
        {MODES.map((option) => (
          <button
            key={option.mode}
            type="button"
            aria-pressed={mode === option.mode}
            onClick={() => {
              setMode(option.mode);
              setError(null);
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
      <form
        className="account-form"
        aria-labelledby="account-title"
        onSubmit={(event) => {
          void submit(event);
        }}
      >
        <label htmlFor="account-username">Username</label>
        <input
          id="account-username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          maxLength={USERNAME_MAX_CHARACTERS}
          value={username}
          onChange={(event) => {
            setUsername(event.target.value);
          }}
        />
        <label htmlFor="account-password">Password</label>
        <input
          id="account-password"
          type="password"
          autoComplete={
            mode === "sign-in" ? "current-password" : "new-password"
          }
          required
          maxLength={PASSWORD_MAX_CHARACTERS}
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />
        {mode === "sign-up" && (
          <p className="dim account-rules">{RULES_TEXT}</p>
        )}
        {error !== null && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button type="submit" className="find-button" disabled={busy}>
          {title}
        </button>
      </form>
    </section>
  );
}

interface SignedInProps {
  username: string;
  onSignedOut: () => void;
}

function SignedIn({ username, onSignedOut }: SignedInProps) {
  const [deleting, setDeleting] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<ApiResult<null>>) {
    setBusy(true);
    setError(null);
    const result = await action();
    setBusy(false);
    if (result.kind === "ok") {
      onSignedOut();
    } else {
      setError(errorText(result));
    }
  }

  return (
    <section className="page account-page" aria-labelledby="account-title">
      <h1 id="account-title">Your account</h1>
      <p className="dim">
        Signed in as <strong className="account-name">{username}</strong>
      </p>
      <div className="account-actions">
        <button
          type="button"
          className="pill-button"
          disabled={busy}
          onClick={() => {
            void run(signOut);
          }}
        >
          Sign out
        </button>
        {!deleting && (
          <button
            type="button"
            className="pill-button"
            onClick={() => {
              setDeleting(true);
            }}
          >
            Delete account
          </button>
        )}
      </div>
      {deleting && (
        <form
          className="account-form"
          onSubmit={(event) => {
            event.preventDefault();
            void run(() => deleteAccount(password));
          }}
        >
          <p>This removes your account and your saved songs.</p>
          <label htmlFor="delete-password">Password</label>
          <input
            id="delete-password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={PASSWORD_MAX_CHARACTERS}
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
          />
          <div className="account-actions">
            <button type="submit" className="find-button" disabled={busy}>
              Delete my account
            </button>
            <button
              type="button"
              className="pill-button"
              onClick={() => {
                setDeleting(false);
                setPassword("");
                setError(null);
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      {error !== null && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </section>
  );
}
