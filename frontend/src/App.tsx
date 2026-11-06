import { Library } from './library/library.tsx'
import { LearnSong } from './lyrics/learn.tsx'
import { NewSong } from './new-song.tsx'
import { Link } from './routes/link.tsx'
import { useRoute } from './routes/route.ts'

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
        <nav className="site-nav" aria-label="Sections">
          <Link href="/" current={screen === 'compose'}>
            Search
          </Link>
          <Link href="/songs" current={screen === 'library'}>
            Songs
          </Link>
        </nav>
      </header>
      <div className="workspace">
        <main className="stage" key={stageKey}>
          {screen === 'library' ? <Library /> : null}
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
      <p className="recovery">
        <Link className="button-primary" href="/">
          Search
        </Link>
        <Link href="/songs">Songs</Link>
      </p>
    </article>
  )
}
