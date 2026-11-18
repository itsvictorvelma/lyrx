// The one search box: a labeled input and the Find button.
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
    <form className="search-form" onSubmit={handleSubmit}>
      <label htmlFor="song-query">Song name or artist</label>
      <div className="search-row">
        <input
          id="song-query"
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
          }}
        />
        <button type="submit" disabled={!canSearch}>
          Find
        </button>
      </div>
    </form>
  );
}
