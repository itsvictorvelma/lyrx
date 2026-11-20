// "Removed <title>" with Undo, at the bottom of the page for a few seconds after Remove.
import { useEffect, useState } from "react";
import type { SavedSong } from "../types";

export const REMOVED_MESSAGE_MS = 6000;

interface RemovedMessageProps {
  song: SavedSong | null;
  onUndo: (song: SavedSong) => void;
  onDone: () => void;
}

// The status area is always on the page, so screen readers announce the message when it appears.
export function RemovedMessage({ song, onUndo, onDone }: RemovedMessageProps) {
  return (
    <div role="status" aria-label="Removed song">
      {song !== null && (
        <RemovedNotice
          key={song.id}
          song={song}
          onUndo={onUndo}
          onDone={onDone}
        />
      )}
    </div>
  );
}

interface RemovedNoticeProps {
  song: SavedSong;
  onUndo: (song: SavedSong) => void;
  onDone: () => void;
}

// The time runs only while neither focus nor the pointer is on the message.
function RemovedNotice({ song, onUndo, onDone }: RemovedNoticeProps) {
  const [held, setHeld] = useState(false);

  useEffect(() => {
    if (held) {
      return;
    }
    const timer = window.setTimeout(onDone, REMOVED_MESSAGE_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [held, onDone]);

  const hold = () => {
    setHeld(true);
  };
  const release = () => {
    setHeld(false);
  };

  return (
    <div
      className="removed-message"
      onFocus={hold}
      onBlur={release}
      onMouseEnter={hold}
      onMouseLeave={release}
    >
      <span>
        Removed{" "}
        <span lang="ja" className="removed-title">
          {song.track}
        </span>
      </span>
      <button
        type="button"
        className="pill-button"
        onClick={() => {
          onUndo(song);
        }}
      >
        Undo
      </button>
    </div>
  );
}
