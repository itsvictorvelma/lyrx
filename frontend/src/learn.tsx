import { useEffect, useRef, useState } from 'react'
import { ApiFailure, getSong } from './api.ts'
import type { SongDetail } from './contracts.ts'
import { Link } from './link.tsx'
import { Player } from './player.tsx'
import {
  languageDirection,
  followScrollTop,
  lyricProblem,
  readFollow,
  readLayers,
  toggleLayer,
  visibleLayerCount,
  writeFollow,
  writeLayers,
  type LayerKey,
  type LayerVisibility,
} from './rehearsal.ts'

const LAYER_OPTIONS: { key: LayerKey; label: string }[] = [
  { key: 'japanese', label: 'Japanese' },
  { key: 'romaji', label: 'Pronunciation (Romaji)' },
  { key: 'meaning', label: 'Direct Meaning' },
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
  const [following, setFollowing] = useState(() => readFollow(browserLayers()))
  const followingRef = useRef(following)
  const lyricsRef = useRef<HTMLOListElement>(null)

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

  useEffect(() => {
    followingRef.current = following
  }, [following])

  useEffect(() => {
    function release(event: Event) {
      if (!followingRef.current) return
      const target = event.target
      if (target instanceof Element && target.closest('.player, button, a, input, label')) return
      followingRef.current = false
      setFollowing(false)
      const storage = browserLayers()
      if (storage) writeFollow(storage, false)
    }

    function releaseFromKey(event: KeyboardEvent) {
      if (!['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '].includes(event.key)) return
      release(event)
    }

    window.addEventListener('wheel', release, { passive: true })
    window.addEventListener('touchmove', release, { passive: true })
    window.addEventListener('keydown', releaseFromKey)
    return () => {
      window.removeEventListener('wheel', release)
      window.removeEventListener('touchmove', release)
      window.removeEventListener('keydown', releaseFromKey)
    }
  }, [])

  function onProgress(current: number, duration: number) {
    if (!followingRef.current || duration <= 0) return
    const list = lyricsRef.current
    if (!list) return
    const listTop = list.getBoundingClientRect().top + window.scrollY
    const start = Math.max(0, listTop - topOffset())
    const end = Math.max(start, listTop + list.offsetHeight - window.innerHeight + bottomGap())
    const next = followScrollTop(current / duration, start, end)
    if (next == null) return
    window.scrollTo(0, next)
  }

  function changeFollow() {
    const next = !following
    followingRef.current = next
    setFollowing(next)
    const storage = browserLayers()
    if (storage) writeFollow(storage, next)
  }

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
          <div className="follow">
            <button type="button" className="layer-toggle" aria-pressed={following} aria-describedby="follow-note" onClick={changeFollow}>
              Follow the song
              <span className="toggle-state">{following ? 'On' : 'Off'}</span>
            </button>
            <p id="follow-note">
              Scrolls the lyrics evenly while the song plays. It does not lock to each line. Scroll yourself to turn
              it off.
            </p>
          </div>
          <Player
            src={state.song.audioUrl}
            durationHint={state.song.durationSeconds}
            following={following && !problem}
            onProgress={onProgress}
          />
          {problem ? (
            <p className="notice" role="alert">
              These lyrics could not be shown.
            </p>
          ) : (
            <ol className="lyrics" ref={lyricsRef}>
              {state.song.lines.map((line) => (
                <li key={line.id} className="lyric">
                  {layers.japanese ? (
                    <p className="lyric-original" lang="ja">
                      <span className="lyric-label">Japanese</span>
                      {line.originalText}
                    </p>
                  ) : null}
                  {layers.romaji ? (
                    <p className="lyric-romaji" lang="ja-Latn">
                      <span className="lyric-label">Pronunciation (Romaji)</span>
                      {line.pronunciationRomaji}
                    </p>
                  ) : null}
                  {layers.meaning ? (
                    <p className="lyric-meaning" lang="en">
                      <span className="lyric-label">Direct Meaning</span>
                      {line.translationEnglish}
                    </p>
                  ) : null}
                </li>
              ))}
            </ol>
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
    <div className="layers" role="group" aria-label="Lyric layers">
      <p id="layer-rule">At least one layer stays visible.</p>
      {LAYER_OPTIONS.map((option) => {
        const shown = layers[option.key]
        return (
          <button
            key={option.key}
            type="button"
            className="layer-toggle"
            aria-pressed={shown}
            aria-describedby="layer-rule"
            disabled={shown && count === 1}
            onClick={() => onToggle(option.key)}
          >
            {option.label}
            <span className="toggle-state">{shown ? 'Shown' : 'Hidden'}</span>
          </button>
        )
      })}
    </div>
  )
}

function topOffset(): number {
  const header = document.querySelector('.site-header')?.getBoundingClientRect().height ?? 0
  const player = document.querySelector('.player')
  if (!player || getComputedStyle(player).position === 'fixed') return header + 16
  return header + player.getBoundingClientRect().height + 16
}

function bottomGap(): number {
  const player = document.querySelector('.player')
  if (!player || getComputedStyle(player).position !== 'fixed') return 16
  return player.getBoundingClientRect().height + 16
}

function browserLayers(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}
