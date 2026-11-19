// The one search box: a labeled input with a search icon and the Find button.
import { useState, type SubmitEvent } from "react";

interface SearchFormProps {
  busy: boolean;
  onSearch: (query: string) => void;
}

export function SearchForm({ busy, onSearch }: SearchFormProps) {
  const [query, setQuery] = useState("");
  const canSearch = !busy && query.trim() !== "";

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSearch) {
      onSearch(query.trim());
    }
  }

  return (
    <form className="search-form" role="search" onSubmit={handleSubmit}>
      <label htmlFor="song-query" className="visually-hidden">
        Song name or artist
      </label>
      <div className="search-box">
        <svg viewBox="0 0 24 24" className="icon" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          id="song-query"
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
