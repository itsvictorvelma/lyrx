// The search box: a labeled input with a search icon and the Find button, in two sizes.
import { useState, type SubmitEvent } from "react";

// The search box shown on the page: the large one on home, the header one elsewhere.
export const SEARCH_INPUT_ID = "song-query";

// For the / shortcut.
export function focusSearchBox(): void {
  document.getElementById(SEARCH_INPUT_ID)?.focus();
}

interface SearchFormProps {
  busy: boolean;
  onSearch: (query: string) => void;
  // "large" on the home page; the header uses the regular size.
  size?: "regular" | "large";
}

export function SearchForm({
  busy,
  onSearch,
  size = "regular",
}: SearchFormProps) {
  const [query, setQuery] = useState("");
  const canSearch = !busy && query.trim() !== "";

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSearch) {
      onSearch(query.trim());
    }
  }

  return (
    <form
      className={size === "large" ? "search-form is-large" : "search-form"}
      role="search"
      onSubmit={handleSubmit}
    >
      <label htmlFor={SEARCH_INPUT_ID} className="visually-hidden">
        Song name or artist
      </label>
      <div className="search-box">
        <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          id={SEARCH_INPUT_ID}
          type="search"
          autoComplete="off"
          placeholder="Title, artist, or both"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
          }}
        />
        <button type="submit" className="find-button" disabled={!canSearch}>
          Find
        </button>
      </div>
    </form>
  );
}
