import { useEffect, useLayoutEffect, useState, type KeyboardEvent } from 'react'
import { ApiFailure, getSong } from './api.ts'
import type { LyricLine, SongDetail } from './contracts.ts'
import { Link } from './link.tsx'
import { Player } from './player.tsx'
import {
  lyricProblem,
  readLayers,
  toggleLayer,
  writeLayers,
  type LayerKey,
  type LayerVisibility,
} from './rehearsal.ts'

const COLUMNS: {
  key: LayerKey
  label: string
  lang: string
  className: string
  text: (line: LyricLine) => string
}[] = [
  { key: 'japanese', label: 'Original', lang: 'ja', className: 'lyric-original', text: (line) => line.originalText },
  { key: 'romaji', label: 'Romaji', lang: 'ja-Latn', className: 'lyric-romaji', text: (line) => line.pronunciationRomaji },
  { key: 'meaning', label: 'English', lang: 'en', className: 'lyric-meaning', text: (line) => line.translationEnglish },
]

type LoadState =
  | { phase: 'loading' }
  | { phase: 'ready'; song: SongDetail }
  | { phase: 'missing' }
  | { phase: 'failed'; message: string }

export function LearnSong({ songId }: { songId: string }) {
  const [state, setState] = useState<LoadState>({ phase: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [layers, setLayers] = useState<LayerVisibility>(() => readLayers(browserLayers()))
  const [reading, setReading] = useState<LayerKey>('japanese')
  const wide = useWideLayout()

  useLayoutEffect(() => {
    document.documentElement.dataset.reading = 'true'
    return () => {
      delete document.documentElement.dataset.reading
    }
  }, [])

  useEffect(() => {
    let active = true
    getSong(songId)
      .then((song) => {
        if (active) setState({ phase: 'ready', song })
      })
      .catch((reason: unknown) => {
        if (!active) return
        if (reason instanceof ApiFailure && (reason.status === 404 || reason.code === 'song_not_found')) {
          setState({ phase: 'missing' })
          return
        }
        const message = reason instanceof Error ? reason.message : 'The song could not be loaded.'
        setState({ phase: 'failed', message })
      })
    return () => {
      active = false
    }
  }, [songId, attempt])

  const problem = state.phase === 'ready' ? lyricProblem(state.song.lines) : null

  useEffect(() => {
    if (state.phase !== 'ready' || !problem) return
    console.error(
      `lyric validation failed song=${state.song.id} version=${state.song.contentVersion} code=${problem}`,
    )
  }, [state, problem])

  function changeLayer(key: LayerKey) {
    const next = toggleLayer(layers, key)
    setLayers(next)
    const storage = browserLayers()
    if (storage) writeLayers(storage, next)
  }

  function retry() {
    setState({ phase: 'loading' })
    setAttempt((value) => value + 1)
  }

  const title =
    state.phase === 'ready' ? state.song.title : state.phase === 'loading' ? 'Loading song' : 'Song unavailable'
  const active = COLUMNS.find((column) => column.key === reading) ?? COLUMNS[0]

  return (
    <article className="learn">
      <Link className="back-link" href="/">
        Song Library
      </Link>
      <h1>{title}</h1>
      {state.phase === 'loading' ? <p role="status">Loading song.</p> : null}
      {state.phase === 'missing' ? (
        <p className="notice" role="alert">
          That song is not available.
        </p>
      ) : null}
      {state.phase === 'failed' ? (
        <div className="notice" role="alert">
          <p>{state.message}</p>
          <button type="button" onClick={retry}>
            Try again
          </button>
        </div>
      ) : null}
      {state.phase === 'ready' ? (
        <>
          <p className="byline">{state.song.artist}</p>
          <div className="learn-tools">
            <Player src={state.song.audioUrl} title={state.song.title} durationHint={state.song.durationSeconds} />
            {!wide && !problem ? (
              <div className="lyric-switch">
                <LyricTabs active={active.key} onSelect={setReading} />
                <LayerToggle label={active.label} shown={layers[active.key]} onToggle={() => changeLayer(active.key)} />
              </div>
            ) : null}
          </div>
          {problem ? (
            <p className="notice" role="alert">
              These lyrics could not be shown.
            </p>
          ) : wide ? (
            <DesktopLyrics song={state.song} layers={layers} onToggle={changeLayer} />
          ) : (
            <LyricDocument
              column={active}
              lines={state.song.lines}
              labelledBy={`tab-${active.key}`}
              shown={layers[active.key]}
            />
          )}
        </>
      ) : null}
    </article>
  )
}

function DesktopLyrics({
  song,
  layers,
  onToggle,
}: {
  song: SongDetail
  layers: LayerVisibility
  onToggle: (key: LayerKey) => void
}) {
  return (
    <div className="lyric-sheet">
      {COLUMNS.map((column) => {
        const shown = layers[column.key]
        return (
          <section key={column.key} className="lyric-pane" aria-labelledby={`pane-${column.key}`}>
            <header className="lyric-pane-title">
              <h2 id={`pane-${column.key}`}>{column.label}</h2>
              <LayerToggle label={column.label} shown={shown} onToggle={() => onToggle(column.key)} />
            </header>
            <LyricBody column={column} lines={song.lines} shown={shown} />
          </section>
        )
      })}
    </div>
  )
}

function LayerToggle({ label, shown, onToggle }: { label: string; shown: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      className="pane-visibility"
      aria-pressed={shown}
      aria-label={`${shown ? 'Hide' : 'Show'} ${label}`}
      onClick={onToggle}
    >
      {shown ? 'Hide' : 'Show'}
    </button>
  )
}

function LyricTabs({ active, onSelect }: { active: LayerKey; onSelect: (key: LayerKey) => void }) {
  function move(event: KeyboardEvent<HTMLButtonElement>, key: LayerKey) {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
    event.preventDefault()
    const index = COLUMNS.findIndex((column) => column.key === key)
    const delta = event.key === 'ArrowRight' ? 1 : -1
    const next = COLUMNS[(index + delta + COLUMNS.length) % COLUMNS.length]
    if (!next) return
    onSelect(next.key)
    const id = `tab-${next.key}`
    requestAnimationFrame(() => document.getElementById(id)?.focus())
  }

  return (
    <div className="lyric-tabs" role="tablist" aria-label="Lyrics">
      {COLUMNS.map((column) => {
        const selected = column.key === active
        return (
          <button
            key={column.key}
            type="button"
            role="tab"
            id={`tab-${column.key}`}
            aria-selected={selected}
            aria-controls={`panel-${column.key}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onSelect(column.key)}
            onKeyDown={(event) => move(event, column.key)}
          >
            {column.label}
          </button>
        )
      })}
    </div>
  )
}

function LyricDocument({
  column,
  lines,
  labelledBy,
  shown,
}: {
  column: (typeof COLUMNS)[number]
  lines: LyricLine[]
  labelledBy: string
  shown: boolean
}) {
  return (
    <section className="lyric-document" role="tabpanel" id={`panel-${column.key}`} aria-labelledby={labelledBy}>
      <h2 className="sr-only">{column.label}</h2>
      <LyricBody column={column} lines={lines} shown={shown} />
    </section>
  )
}

function LyricBody({
  column,
  lines,
  shown,
}: {
  column: (typeof COLUMNS)[number]
  lines: LyricLine[]
  shown: boolean
}) {
  return (
    <div className={shown ? column.className : `${column.className} is-hidden`} lang={column.lang} aria-hidden={shown ? undefined : true}>
      {lines.map((line) => (
        <p key={line.id}>{column.text(line)}</p>
      ))}
    </div>
  )
}

function useWideLayout(): boolean {
  const [wide, setWide] = useState(() => window.matchMedia('(min-width: 48rem)').matches)
  useEffect(() => {
    const query = window.matchMedia('(min-width: 48rem)')
    const update = () => setWide(query.matches)
    update()
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])
  return wide
}

function browserLayers(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}
