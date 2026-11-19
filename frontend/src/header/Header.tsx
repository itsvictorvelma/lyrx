// The bar on every page: the lyrx wordmark (back to the library), the search box, the theme button.
import { navigate } from "../routing";
import { SearchForm } from "./SearchForm";
import { ThemeButton } from "./ThemeButton";

interface HeaderProps {
  busy: boolean;
  onSearch: (query: string) => void;
}

export function Header({ busy, onSearch }: HeaderProps) {
  return (
    <header className="site-header">
      <a
        href="/"
        className="wordmark"
        onClick={(event) => {
          event.preventDefault();
          navigate("/");
        }}
      >
        lyrx{" "}
        <span lang="ja" className="wordmark-kana">
          歌詞
        </span>
      </a>
      <SearchForm busy={busy} onSearch={onSearch} />
      <ThemeButton />
    </header>
  );
}
