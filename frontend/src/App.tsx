import { ImportPage } from './import-form.tsx'
import { LearnSong } from './learn.tsx'
import { Library } from './library.tsx'
import { Link } from './link.tsx'
import { useRoute } from './route.ts'

export default function App() {
  const route = useRoute()

  return (
    <>
      <header className="site-header">
        <Link className="wordmark" href="/">
          Lyrx
        </Link>
      </header>
      <main>
        {route.name === 'library' ? <Library /> : null}
        {route.name === 'import' ? <ImportPage /> : null}
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
      <p>
        <Link href="/">Song Library</Link>
      </p>
    </>
  )
}
