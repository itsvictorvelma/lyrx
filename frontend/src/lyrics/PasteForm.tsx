// The paste form: a labeled text area, the submit button, and the waiting status.
import { useState, type Ref, type SubmitEvent } from "react";

const WAITING_TEXT = "Working on your lyrics…";

interface PasteFormProps {
  waiting: boolean;
  onSubmit: (lyrics: string) => void;
  textAreaRef?: Ref<HTMLTextAreaElement>;
}

export function PasteForm({ waiting, onSubmit, textAreaRef }: PasteFormProps) {
  const [lyrics, setLyrics] = useState("");
  const canSubmit = !waiting && lyrics.trim() !== "";

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) {
      onSubmit(lyrics);
    }
  }

  return (
    <form className="paste-form" onSubmit={handleSubmit}>
      <label htmlFor="lyrics">Japanese lyrics</label>
      <textarea
        ref={textAreaRef}
        id="lyrics"
        rows={12}
        value={lyrics}
        onChange={(event) => {
          setLyrics(event.target.value);
        }}
      />
      <button type="submit" disabled={!canSubmit}>
        Get four versions
      </button>
      <p role="status" aria-live="polite">
        {waiting ? WAITING_TEXT : ""}
      </p>
    </form>
  );
}
