// The paste fallback: a labeled text area and its submit button.
import { useState, type SubmitEvent } from "react";

interface PasteFormProps {
  busy: boolean;
  onSubmit: (lyrics: string) => void;
}

export function PasteForm({ busy, onSubmit }: PasteFormProps) {
  const [lyrics, setLyrics] = useState("");
  const canSubmit = !busy && lyrics.trim() !== "";

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
        id="lyrics"
        rows={12}
        value={lyrics}
        onChange={(event) => {
          setLyrics(event.target.value);
        }}
      />
      <button type="submit" disabled={!canSubmit}>
        Show the versions
      </button>
    </form>
  );
}
