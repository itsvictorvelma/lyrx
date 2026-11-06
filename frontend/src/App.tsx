import { useEffect, useRef, useState } from 'react'
import { Library } from './library/library.tsx'
import { LearnSong } from './lyrics/learn.tsx'
import { NewSong } from './new-song.tsx'
import { Link } from './routes/link.tsx'
import { useRoute, type Route } from './routes/route.ts'

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
        <SiteMenu key={stageKey} route={route} />
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

function SiteMenu({ route }: { route: Route }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (open) return
    const panel = rootRef.current?.querySelector('#site-menu-panel')
    const active = document.activeElement
    if (panel && active instanceof Node && panel.contains(active)) buttonRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKey(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      setOpen(false)
      buttonRef.current?.focus()
    }
    function onPointer(event: PointerEvent) {
      const target = event.target
      if (!(target instanceof Node) || rootRef.current?.contains(target)) return
      setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onPointer)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onPointer)
    }
  }, [open])

  return (
    <nav className="site-menu" aria-label="Library and new song" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="menu-button"
        aria-expanded={open}
        aria-controls="site-menu-panel"
        onClick={() => setOpen((value) => !value)}
      >
        Menu
      </button>
      <ul id="site-menu-panel" className="site-menu-panel" hidden={!open} onClick={() => setOpen(false)}>
        <li>
          <Link className="menu-link" href="/songs/new" current={route.name === 'compose'}>
            New song
          </Link>
        </li>
        <li>
          <Link className="menu-link" href="/songs" current={route.name === 'library'}>
            Song Library
          </Link>
        </li>
      </ul>
    </nav>
  )
}

function MissingPage() {
  return (
    <article className="stage-home">
      <h1>Page not found</h1>
      <p className="lede">That page is not available.</p>
      <Link className="button-primary" href="/">
        New song
      </Link>
    </article>
  )
}
