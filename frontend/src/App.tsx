import { Library } from './library/library.tsx'
import { LearnSong } from './lyrics/learn.tsx'
import { NewSong } from './new-song.tsx'
import { Link } from './routes/link.tsx'
import { useRoute } from './routes/route.ts'

export default function App() {
  const route = useRoute()
  const screen = route.name === 'song' ? 'song' : route.name
  const stageKey = route.name === 'song' ? route.songId : screen
  const showRail = screen === 'compose' || screen === 'song'

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
        {showRail ? (
          <aside className="rail" aria-label="Saved songs">
            <Library activeId={route.name === 'song' ? route.songId : null} />
          </aside>
        ) : null}
        <main className="stage" key={stageKey}>
          {screen === 'library' ? <Library variant="page" /> : null}
          {screen === 'compose' ? <NewSong /> : null}
          {route.name === 'song' ? <LearnSong key={route.songId} songId={route.songId} /> : null}
          {screen === 'missing' ? <MissingPage /> : null}
        </main>
      </div>
    </div>
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
