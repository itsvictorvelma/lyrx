import { NewSong } from './new-song.tsx'
import { LearnSong } from './learn.tsx'
import { Library } from './library.tsx'
import { Link } from './link.tsx'
import { useRoute } from './route.ts'

export default function App() {
  const route = useRoute()
  const screen = route.name === 'song' ? 'song' : route.name
  const stageKey = route.name === 'song' ? route.songId : screen

  return (
    <div className="shell" data-screen={screen}>
      <header className="site-header">
        <Link className="wordmark" href="/">
          Lyrx
        </Link>
        <Link className="button-primary" href="/songs/new" current={screen === 'compose'}>
          New song
        </Link>
      </header>
      <div className="workspace">
        {screen === 'missing' ? null : (
          <aside className="rail" aria-label="Saved songs">
            <Library activeId={route.name === 'song' ? route.songId : null} />
          </aside>
        )}
        <main className="stage" key={stageKey}>
          {screen === 'library' ? <StageHome /> : null}
          {screen === 'compose' ? <NewSong /> : null}
          {route.name === 'song' ? <LearnSong key={route.songId} songId={route.songId} /> : null}
          {screen === 'missing' ? <MissingPage /> : null}
        </main>
      </div>
    </div>
  )
}

function StageHome() {
  return (
    <article className="stage-home">
      <p className="kicker">Lyrx</p>
      <h1>Pick a song, or start one.</h1>
      <p className="lede">The original, the reading, the romaji, and the English stay open together.</p>
      <Link className="button-primary" href="/songs/new">
        New song
      </Link>
    </article>
  )
}

function MissingPage() {
  return (
    <article className="stage-home">
      <h1>Page not found</h1>
      <p className="lede">That page is not available.</p>
      <Link className="button-primary" href="/">
        Back to songs
      </Link>
    </article>
  )
}
