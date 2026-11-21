// The home page: the hero line, the large search, how it works or Continue, recent songs, footer.
import { isGuest, useAccount } from "../account/account";
import { SearchForm } from "../search/SearchForm";
import { SongArt } from "../library/SongArt";
import type { RecentSong, SavedSong } from "../types";
import { ACCOUNT_PATH, followLink, LIBRARY_PATH } from "../routing";
import { HeroLine } from "./HeroLine";

export const SOURCE_CODE_URL = "https://github.com/itsvictorvelma/subbed";
const LRCLIB_URL = "https://lrclib.net";

const STEPS = [
  {
    title: "Find a song",
    body: "Type a title, an artist, or both. The lyrics come from LRCLIB.",
  },
  {
    title: "Read every line four ways",
    body: "Original, hiragana, romaji, and English, one row per line.",
  },
  {
    title: "Play along and practise",
    body: "Add the YouTube video, loop a line, or hide a column to test yourself.",
  },
];

interface HomePageProps {
  savedSongs: SavedSong[];
  recentSongs: RecentSong[];
  onSearch: (query: string) => void;
  onOpenSong: (id: number) => void;
}

export function HomePage(props: HomePageProps) {
  const guest = isGuest(useAccount());
  // A guest has no saved songs, so never a Continue card.
  const lastOpened = mostRecent(props.savedSongs);

  return (
    <div className="home">
      <section className="home-hero" aria-labelledby="home-title">
        <h1 id="home-title" className="home-title">
          Read any Japanese song, line by line.
        </h1>
        <HeroLine />
        {/* Home is never shown mid-search: the loading steps replace it. */}
        <SearchForm busy={false} onSearch={props.onSearch} size="large" />
        <p className="home-hint">
          Press <kbd>/</kbd> to search, <kbd>?</kbd> for all keyboard shortcuts
        </p>
        {guest && (
          <p className="home-hint">
            <a
              href={ACCOUNT_PATH}
              className="home-sign-in"
              onClick={followLink(ACCOUNT_PATH)}
            >
              Sign in
            </a>{" "}
            to save songs.
          </p>
        )}
      </section>
      {lastOpened === null ? (
        <HowItWorks />
      ) : (
        <ContinueCard
          song={lastOpened}
          savedCount={props.savedSongs.length}
          onOpen={props.onOpenSong}
        />
      )}
      {props.recentSongs.length > 0 && (
        <RecentSongs songs={props.recentSongs} onOpen={props.onOpenSong} />
      )}
      <HomeFooter />
    </div>
  );
}

function mostRecent(songs: SavedSong[]): SavedSong | null {
  return songs.reduce<SavedSong | null>(
    (latest, song) =>
      latest === null || song.lastOpenedAt > latest.lastOpenedAt
        ? song
        : latest,
    null,
  );
}

function HowItWorks() {
  return (
    <section className="home-section" aria-labelledby="how-title">
      <h2 id="how-title">How Subbed works</h2>
      <ol className="home-steps">
        {STEPS.map((step) => (
          <li key={step.title}>
            <h3>{step.title}</h3>
            <p className="dim">{step.body}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

interface ContinueCardProps {
  song: SavedSong;
  savedCount: number;
  onOpen: (id: number) => void;
}

function ContinueCard({ song, savedCount, onOpen }: ContinueCardProps) {
  return (
    <section className="home-section" aria-labelledby="continue-title">
      <h2 id="continue-title">Pick up where you left off</h2>
      <div className="continue-row">
        <button
          type="button"
          className="continue-card"
          aria-label={`Continue ${song.track} by ${song.artist}`}
          onClick={() => {
            onOpen(song.id);
          }}
        >
          <SongArt track={song.track} videoId={song.videoId} />
          <span className="continue-text">
            <span lang="ja" className="continue-title">
              {song.track}
            </span>
            <span className="dim">{song.artist}</span>
            <span className="continue-action">Continue</span>
          </span>
        </button>
        <a
          href={LIBRARY_PATH}
          className="text-link"
          onClick={followLink(LIBRARY_PATH)}
        >
          All your songs ({savedCount})
        </a>
      </div>
    </section>
  );
}

interface RecentSongsProps {
  songs: RecentSong[];
  onOpen: (id: number) => void;
}

function RecentSongs({ songs, onOpen }: RecentSongsProps) {
  return (
    <section className="home-section" aria-labelledby="recent-title">
      <div className="home-section-head">
        <h2 id="recent-title">Songs already in Subbed</h2>
        <p className="dim">Already translated, so they open instantly.</p>
      </div>
      <ul className="recent-row">
        {songs.map((song) => (
          <li key={song.id}>
            <button
              type="button"
              className="tile-open"
              aria-label={`Open ${song.track} by ${song.artist}`}
              onClick={() => {
                onOpen(song.id);
              }}
            >
              <SongArt track={song.track} videoId={song.videoId} />
              <span lang="ja" className="tile-title recent-title">
                {song.track}
              </span>
              <span className="tile-meta">{song.artist}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function HomeFooter() {
  return (
    <footer className="home-footer">
      <div>
        <p>
          Lyrics from <a href={LRCLIB_URL}>LRCLIB</a>. Hiragana, romaji, and
          English by Groq and Gemini.
        </p>
        <p>
          Built by Victor Velma. <a href={SOURCE_CODE_URL}>Source on GitHub</a>
        </p>
      </div>
      <p>
        Press <kbd>?</kbd> for keyboard shortcuts
      </p>
    </footer>
  );
}
