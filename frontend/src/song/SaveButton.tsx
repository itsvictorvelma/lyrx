// The Save / Saved toggle on a song: puts the song (with its video and sync) in the library, or takes it out.
// A guest is sent to sign in, then back to the song.
import { useState } from "react";
import { isGuest, useAccount } from "../account/account";
import { accountPath, navigate, songPath } from "../routing";
import { saveSong, unsaveSong } from "../api";
import type { Playback } from "../types";
import { BookmarkIcon } from "../icons";

const SAVE_SONG_FAILED_MESSAGE = "Couldn't update your songs. Try again.";

interface SaveButtonProps {
  songId: number;
  saved: boolean;
  // The video and sync now in the player bar, kept with the song when it is saved.
  playback: Playback;
  onSavedChange: (saved: boolean) => void;
}

export function SaveButton(props: SaveButtonProps) {
  const { songId, saved, playback, onSavedChange } = props;
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const guest = isGuest(useAccount());

  async function toggle() {
    if (guest) {
      navigate(accountPath(songPath(songId)));
      return;
    }
    setBusy(true);
    setFailed(false);
    const result = saved
      ? await unsaveSong(songId)
      : await saveSong(songId, playback);
    setBusy(false);
    if (result.kind === "ok") {
      onSavedChange(!saved);
    } else {
      setFailed(true);
    }
  }

  return (
    <>
      <button
        type="button"
        className={
          saved ? "pill-button save-button is-saved" : "pill-button save-button"
        }
        aria-pressed={saved}
        disabled={busy}
        onClick={() => {
          void toggle();
        }}
      >
        <BookmarkIcon filled={saved} /> {saved ? "Saved" : "Save"}
      </button>
      {failed && (
        <span role="alert" className="error save-error">
          {SAVE_SONG_FAILED_MESSAGE}
        </span>
      )}
    </>
  );
}
