// The bar on every page: the wordmark, the search box, Home, Your songs, Sign in or the username,
// and the theme button.
import type { MouseEvent } from "react";
import { useAccount } from "../account/account";
import { ACCOUNT_PATH, HOME_PATH, LIBRARY_PATH, navigate } from "../routing";
import type { Route } from "../routing";
import { SearchForm } from "../search/SearchForm";
import { ThemeButton } from "./ThemeButton";

interface HeaderProps {
  busy: boolean;
  onSearch: (query: string) => void;
  // False on the home page, which has its own large search box.
  showSearch: boolean;
  // Which page is shown, so its link is marked as the current page.
  currentPage: Route["page"];
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
  currentPage,
}: HeaderProps) {
  const { username, checked } = useAccount();
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
          href={HOME_PATH}
          className="nav-link"
          aria-current={currentPage === "home" ? "page" : undefined}
          onClick={moveTo(HOME_PATH)}
        >
          Home
        </a>
        <a
          href={LIBRARY_PATH}
          className="nav-link"
          aria-current={currentPage === "library" ? "page" : undefined}
          onClick={moveTo(LIBRARY_PATH)}
        >
          Your songs
        </a>
        {checked && (
          <a
            href={ACCOUNT_PATH}
            className="nav-link"
            aria-current={currentPage === "account" ? "page" : undefined}
            onClick={moveTo(ACCOUNT_PATH)}
          >
            {username ?? "Sign in"}
          </a>
        )}
        <ThemeButton />
      </nav>
    </header>
  );
}
