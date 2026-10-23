import { useEffect, useRef, useState } from 'react'
import { ApiFailure, getSong } from './api.ts'
import type { SongDetail } from './contracts.ts'
import { Link } from './link.tsx'
import { Player } from './player.tsx'
import {
  defaultSecondsPerLine,
  formatTime,
  languageDirection,
  lyricProblem,
  readFollow,
  readLayers,
  readPace,
  secondsPerLineFromBpm,
  singingLineIndex,
  toggleLayer,
  visibleLayerCount,
  writeFollow,
  writeLayers,
  writePace,
  type LayerKey,
  type LayerVisibility,
  type SongPace,
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
  const [pace, setPace] = useState<SongPace>(() => readPace(browserStore(), songId))
  const [paceNote, setPaceNote] = useState<string | null>(null)
  const followingRef = useRef(following)
  const paceRef = useRef(pace)
  const lyricsRef = useRef<HTMLOListElement>(null)
  const timeRef = useRef(0)
  const durationRef = useRef(0)
  const lineCountRef = useRef(0)
  const lastLineRef = useRef(-1)
  const bpmRef = useRef<HTMLInputElement>(null)
  const beatsRef = useRef<HTMLInputElement>(null)

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
    paceRef.current = pace
    lineCountRef.current = state.phase === 'ready' ? state.song.lines.length : 0
  }, [following, pace, state])

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
    timeRef.current = current
    durationRef.current = duration
    if (!followingRef.current || duration <= 0) return
    const paceNow = paceRef.current
    const seconds = paceNow.secondsPerLine ?? defaultSecondsPerLine(duration, lineCountRef.current, paceNow.introSeconds)
    if (seconds == null) return
    const index = singingLineIndex(current, paceNow.introSeconds, seconds, lineCountRef.current)
    if (index == null || index === lastLineRef.current) return
    lastLineRef.current = index
    const line = lyricsRef.current?.querySelector(`[data-index="${index}"]`)
    if (!(line instanceof HTMLElement)) return
    window.scrollTo(0, Math.max(0, line.getBoundingClientRect().top + window.scrollY - topOffset()))
  }

  function savePace(next: SongPace) {
    paceRef.current = next
    lastLineRef.current = -1
    setPace(next)
    const storage = browserStore()
    if (storage) writePace(storage, songId, next)
  }

  function markStart() {
    savePace({ ...paceRef.current, introSeconds: Math.max(0, timeRef.current) })
    setPaceNote(null)
  }

  function nudge(factor: number) {
    const current =
      paceRef.current.secondsPerLine ??
      defaultSecondsPerLine(durationRef.current, lineCountRef.current, paceRef.current.introSeconds)
    if (current == null) return
    savePace({ ...paceRef.current, secondsPerLine: Math.min(20, Math.max(0.4, current * factor)) })
    setPaceNote(null)
  }

  function useTempo() {
    const seconds = secondsPerLineFromBpm(Number(bpmRef.current?.value), Number(beatsRef.current?.value))
    if (seconds == null) {
      setPaceNote('Enter a tempo from 40 to 300, and how many beats one line takes.')
      return
    }
    savePace({ ...paceRef.current, secondsPerLine: seconds })
    setPaceNote(null)
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
              Moves at one steady pace for this song. Entrances, rests, and uneven lines still throw it off. Scroll yourself to turn it off.
            </p>
            <p>Singing starts at {formatTime(pace.introSeconds)}. Saved on this song only.</p>
            <div className="pace">
              <button type="button" onClick={markStart}>
                Mark singing start
              </button>
              <button type="button" onClick={() => nudge(0.85)}>
                Faster
              </button>
              <button type="button" onClick={() => nudge(1.15)}>
                Slower
              </button>
            </div>
            <div className="pace">
              <label>
                BPM
                <input ref={bpmRef} type="number" min={40} max={300} step={1} inputMode="numeric" />
              </label>
              <label>
                Beats per line
                <input ref={beatsRef} type="number" min={1} max={32} step={1} defaultValue={4} inputMode="numeric" />
              </label>
              <button type="button" onClick={useTempo}>
                Use tempo
              </button>
            </div>
            <p>
              {pace.secondsPerLine
                ? `About ${pace.secondsPerLine.toFixed(1)} seconds per line.`
                : 'Without a tempo, each line shares the time after the start. A tempo is still one steady pace.'}
            </p>
            {paceNote ? <p role="alert">{paceNote}</p> : null}
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
                <li key={line.id} className="lyric" data-index={line.index}>
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

function browserLayers(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function browserStore(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}
