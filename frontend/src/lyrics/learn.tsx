import { useEffect, useLayoutEffect, useState, type KeyboardEvent } from 'react'
import { ApiFailure, getSong } from '../api.ts'
import type { LyricLine, SongDetail } from '../contracts.ts'
import { AudioAttach } from '../player/audio-form.tsx'
import { Player } from '../player/player.tsx'
import { Link } from '../routes/link.tsx'
import { COLUMNS } from './columns.ts'
import { lineRowStyle, useWideLayout } from './layout.ts'
import { readLayers, toggleLayer, writeLayers, type LayerKey, type LayerVisibility } from './layers.ts'
import { lineIndexFromValue, linkedLineIndex, lyricProblem } from './lines.ts'

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

  const ready = state.phase === 'ready'

  return (
    <article className="learn">
      <header className="learn-mast">
        <h1 className={ready ? 'song-name' : undefined} lang={ready ? 'ja' : undefined}>
          {title}
        </h1>
        {ready ? <p className="byline">{state.song.artist}</p> : null}
      </header>
      {state.phase === 'loading' ? <p role="status">Loading song.</p> : null}
      {state.phase === 'missing' ? (
        <div className="notice" role="alert">
          <p>That song is not available.</p>
          <ul className="recovery-links">
            <li>
              <Link href="/songs/new">New song</Link>
            </li>
            <li>
              <Link href="/songs">Song Library</Link>
            </li>
          </ul>
        </div>
      ) : null}
      {state.phase === 'failed' ? (
        <div className="notice" role="alert">
          <p>{state.message}</p>
          <button type="button" onClick={retry}>
            Try again
          </button>
        </div>
      ) : null}
      {ready ? (
        <>
          <div className="learn-tools">
            <Player src={state.song.audioUrl} title={state.song.title} durationHint={state.song.durationSeconds} />
            <AudioAttach songId={songId} hasAudio={Boolean(state.song.audioUrl)} onAttached={retry} />
            {!wide && !problem ? (
              <div className="lyric-switch">
                <LyricTabs active={active.key} onSelect={setReading} />
                <LayerToggle label={active.label} shown={layers[active.key]} onToggle={() => changeLayer(active.key)} />
              </div>
            ) : null}
          </div>
          <div className="learn-reading">
            {problem ? (
              <p className="notice" role="alert">
                These lyrics could not be shown.
              </p>
            ) : wide ? (
              <DesktopLyrics lines={state.song.lines} layers={layers} onToggle={changeLayer} />
            ) : (
              <LyricDocument
                column={active}
                lines={state.song.lines}
                labelledBy={`tab-${active.key}`}
                shown={layers[active.key]}
              />
            )}
          </div>
        </>
      ) : null}
    </article>
  )
}

export function DesktopLyrics({
  lines,
  layers,
  onToggle,
}: {
  lines: LyricLine[]
  layers: LayerVisibility
  onToggle: (key: LayerKey) => void
}) {
  const [hoverLine, setHoverLine] = useState<number | null>(null)
  const [focusLine, setFocusLine] = useState<number | null>(null)
  const visibleDocuments = COLUMNS.filter((column) => layers[column.key]).length
  const activeLine = linkedLineIndex(hoverLine, focusLine, visibleDocuments)

  return (
    <div
      className="lyric-sheet"
      style={lineRowStyle(lines.length)}
      onPointerOver={(event) => setHoverLine(lineIndexFromValue(datasetLine(event.target)))}
      onPointerLeave={() => setHoverLine(null)}
      onFocus={(event) => setFocusLine(lineIndexFromValue(datasetLine(event.target)))}
      onBlur={(event) => {
        const next = event.relatedTarget
        if (next instanceof Node && event.currentTarget.contains(next)) return
        setFocusLine(null)
      }}
    >
      {COLUMNS.map((column) => {
        const shown = layers[column.key]
        return (
          <section key={column.key} className="lyric-pane" aria-labelledby={`pane-${column.key}`}>
            <header className="lyric-pane-title">
              <h2 id={`pane-${column.key}`}>{column.label}</h2>
              <LayerToggle label={column.label} shown={shown} onToggle={() => onToggle(column.key)} />
            </header>
            <LyricBody
              column={column}
              lines={lines}
              shown={shown}
              correspond={visibleDocuments >= 2}
              activeLine={activeLine}
            />
          </section>
        )
      })}
    </div>
  )
}

export function LayerToggle({ label, shown, onToggle }: { label: string; shown: boolean; onToggle: () => void }) {
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

export function LyricTabs({ active, onSelect }: { active: LayerKey; onSelect: (key: LayerKey) => void }) {
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

export function LyricDocument({
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
  correspond = false,
  activeLine = null,
}: {
  column: (typeof COLUMNS)[number]
  lines: LyricLine[]
  shown: boolean
  correspond?: boolean
  activeLine?: number | null
}) {
  const empty = lines.every((line) => column.text(line).trim() === '')
  if (empty && !correspond) {
    const hidden = shown ? '' : ' is-hidden'
    return (
      <div className={`lyric-body ${column.className}${hidden}`} lang={column.lang} aria-hidden={shown ? undefined : true}>
        <p className="lyric-empty">Nothing here yet.</p>
      </div>
    )
  }
  return (
    <div
      className={shown ? `lyric-body ${column.className}` : `lyric-body ${column.className} is-hidden`}
      lang={column.lang}
      aria-hidden={shown ? undefined : true}
    >
      {lines.map((line) => {
        if (empty) {
          return (
            <p key={line.id} className={line.index === 0 ? 'lyric-empty' : undefined}>
              {line.index === 0 ? 'Nothing here yet.' : ''}
            </p>
          )
        }
        if (!correspond) return <p key={line.id}>{column.text(line)}</p>
        return (
          <p key={line.id}>
            <span
              className={activeLine === line.index ? 'lyric-line is-linked' : 'lyric-line'}
              data-line={line.index}
              tabIndex={shown ? 0 : undefined}
            >
              {column.text(line)}
            </span>
          </p>
        )
      })}
    </div>
  )
}

function datasetLine(target: EventTarget | null): string | null {
  if (!(target instanceof Element)) return null
  const row = target.closest('[data-line]')
  if (!(row instanceof HTMLElement)) return null
  return row.dataset.line ?? null
}

function browserLayers(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}
