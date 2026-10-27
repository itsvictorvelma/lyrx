import { useEffect, useState } from 'react'
import { ApiFailure, getSong } from './api.ts'
import type { LyricLine, SongDetail } from './contracts.ts'
import { Link } from './link.tsx'
import { Player } from './player.tsx'
import {
  languageDirection,
  lyricProblem,
  readLayers,
  toggleLayer,
  visibleLayerCount,
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
  {
    key: 'romaji',
    label: 'Pronunciation (Romaji)',
    lang: 'ja-Latn',
    className: 'lyric-romaji',
    text: (line) => line.pronunciationRomaji,
  },
  {
    key: 'meaning',
    label: 'Direct English',
    lang: 'en',
    className: 'lyric-meaning',
    text: (line) => line.translationEnglish,
  },
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
    if (!next) return
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
  const visible = COLUMNS.filter((column) => layers[column.key])

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
          <p className="song-meta">
            {languageDirection(state.song.sourceLanguage, state.song.targetLanguage)}
          </p>
          <LayerToggles layers={layers} onToggle={changeLayer} />
          <Player src={state.song.audioUrl} durationHint={state.song.durationSeconds} />
          {problem ? (
            <p className="notice" role="alert">
              These lyrics could not be shown.
            </p>
          ) : (
            <div className="lyric-sheet" tabIndex={0}>
              <table className="lyric-table" data-columns={visible.length}>
                <caption>Lyrics</caption>
                <thead>
                  <tr>
                    {visible.map((column) => (
                      <th key={column.key} scope="col">
                        {column.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {state.song.lines.map((line) => (
                    <tr key={line.id}>
                      {visible.map((column) => (
                        <td key={column.key} className={column.className} lang={column.lang}>
                          {column.text(line)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </article>
  )
}

function LayerToggles({
  layers,
  onToggle,
}: {
  layers: LayerVisibility
  onToggle: (key: LayerKey) => void
}) {
  const count = visibleLayerCount(layers)
  return (
    <div className="layers" role="group" aria-label="Lyric columns">
      <p id="layer-rule">At least one column stays visible.</p>
      {COLUMNS.map((column) => {
        const shown = layers[column.key]
        return (
          <button
            key={column.key}
            type="button"
            className="layer-toggle"
            aria-pressed={shown}
            aria-describedby="layer-rule"
            disabled={shown && count === 1}
            onClick={() => onToggle(column.key)}
          >
            {column.label}
            <span className="toggle-state">{shown ? 'Shown' : 'Hidden'}</span>
          </button>
        )
      })}
    </div>
  )
}

function browserLayers(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}
