import { Home } from './home.tsx'
import { NewSong } from './new-song.tsx'
import { LearnSong } from './learn.tsx'
import { Library } from './library.tsx'
import { Link } from './link.tsx'
import { useRoute } from './route.ts'

export default function App() {
  const route = useRoute()
  const pageKey = route.name === 'song' ? route.songId : route.name

  return (
    <>
      <header className="site-header">
        <Link className="wordmark" href="/">
          Lyrx
        </Link>
        <nav className="site-nav" aria-label="Pages">
          <Link className="nav-link" href="/songs" current={route.name === 'library'}>
            Library
          </Link>
          <Link className="nav-link" href="/search" current={route.name === 'search'}>
            Search
          </Link>
        </nav>
      </header>
      <main className="page" key={pageKey}>
        {route.name === 'home' ? <Home /> : null}
        {route.name === 'library' ? <Library /> : null}
        {route.name === 'search' ? <NewSong /> : null}
        {route.name === 'song' ? <LearnSong key={route.songId} songId={route.songId} /> : null}
        {route.name === 'missing' ? <MissingPage /> : null}
      </main>
    </>
  )
}

function MissingPage() {
  return (
    <>
      <h1>Page not found</h1>
      <p>That page is not available.</p>
      <p className="home-actions">
        <Link href="/">Home</Link>
        <Link href="/songs">Song Library</Link>
      </p>
    </>
  )
}
