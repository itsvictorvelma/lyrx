// The bar on every page: the lyrx wordmark (home), the search box, Your songs, the theme button.
import type { MouseEvent } from "react";
import { HOME_PATH, LIBRARY_PATH, navigate } from "../routing";
import { SearchForm } from "./SearchForm";
import { ThemeButton } from "./ThemeButton";

interface HeaderProps {
  busy: boolean;
  onSearch: (query: string) => void;
  // False on the home page, which has its own large search box.
  showSearch: boolean;
  // True on the library, so its link is marked as the current page.
  isLibraryPage: boolean;
}

// A same-site link that moves without reloading the page.
function moveTo(path: string) {
  return (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    navigate(path);
  };
}

export function Header({
  busy,
  onSearch,
  showSearch,
  isLibraryPage,
}: HeaderProps) {
  return (
    <header className="site-header">
      <a href={HOME_PATH} className="wordmark" onClick={moveTo(HOME_PATH)}>
        lyrx{" "}
        <span lang="ja" className="wordmark-kana">
          歌詞
        </span>
      </a>
      {showSearch && <SearchForm busy={busy} onSearch={onSearch} />}
      <nav className="site-nav" aria-label="Main">
        <a
          href={LIBRARY_PATH}
          className="nav-link"
          aria-current={isLibraryPage ? "page" : undefined}
          onClick={moveTo(LIBRARY_PATH)}
        >
          Your songs
        </a>
        <ThemeButton />
      </nav>
    </header>
  );
}
