import { useEffect, useRef, useState } from 'react'
import { ApiFailure, getSong, saveLineTimes, scanSong } from './api.ts'
import type { SongDetail } from './contracts.ts'
import { Link } from './link.tsx'
import { Player } from './player.tsx'
import {
  activeLineIndex,
  formatTime,
  hasLineTime,
  languageDirection,
  lyricProblem,
  readFollow,
  readLayers,
  readLineStarts,
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
  const [timingNote, setTimingNote] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [stampIndex, setStampIndex] = useState(0)
  const [seekRequest, setSeekRequest] = useState<{ time: number; token: number } | null>(null)
  const followingRef = useRef(following)
  const startsRef = useRef<(number | null)[]>([])
  const seekToken = useRef(0)
  const lyricsRef = useRef<HTMLOListElement>(null)
  const timeRef = useRef(0)
  const lastLineRef = useRef(-1)

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
    startsRef.current = state.phase === 'ready' ? readLineStarts(state.song.lines) : []
    paintLine(lyricsRef.current, lastLineRef.current)
  }, [following, state])

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

  function onProgress(current: number, _duration: number) {
    timeRef.current = current
    const starts = startsRef.current
    const index = hasLineTime(starts) ? activeLineIndex(current, starts) : null
    const lineIndex = index ?? -1
    if (lineIndex === lastLineRef.current) return
    lastLineRef.current = lineIndex
    paintLine(lyricsRef.current, lineIndex)
    if (!followingRef.current || index == null) return
    const line = lyricsRef.current?.querySelector(`[data-index="${index}"]`)
    if (!(line instanceof HTMLElement)) return
    window.scrollTo(0, Math.max(0, line.getBoundingClientRect().top + window.scrollY - topOffset()))
  }

  async function stamp(index: number) {
    if (state.phase !== 'ready' || saving) return
    setSaving(true)
    setTimingNote(null)
    try {
      const song = await saveLineTimes(songId, [{ index, startSeconds: Math.max(0, timeRef.current) }])
      lastLineRef.current = -1
      setState({ phase: 'ready', song })
      setStampIndex(Math.min(song.lines.length - 1, index + 1))
    } catch (reason) {
      setTimingNote(reason instanceof Error ? reason.message : 'The line time could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  async function scan() {
    if (saving) return
    setSaving(true)
    setTimingNote('Scanning the song. The first scan downloads a speech model and can take a few minutes.')
    try {
      const song = await scanSong(songId)
      lastLineRef.current = -1
      setState({ phase: 'ready', song })
      setTimingNote('Line times are saved. Move a line if it comes in early or late.')
    } catch (reason) {
      setTimingNote(reason instanceof Error ? reason.message : 'The scan failed.')
    } finally {
      setSaving(false)
    }
  }

  function playFrom(time: number) {
    seekToken.current += 1
    setSeekRequest({ time, token: seekToken.current })
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
          <FollowControls
            timed={hasLineTime(readLineStarts(state.song.lines))}
            following={following}
            timingNote={timingNote}
            saving={saving}
            stampLabel={state.song.lines[Math.min(stampIndex, state.song.lines.length - 1)]?.originalText ?? ''}
            onFollow={changeFollow}
            onStampNext={() => {
              const index = Math.min(stampIndex, state.song.lines.length - 1)
              if (index >= 0) void stamp(index)
            }}
            onScan={() => void scan()}
          />
          <Player
            src={state.song.audioUrl}
            durationHint={state.song.durationSeconds}
            following={following && !problem}
            seekRequest={seekRequest}
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
                  <p className="lyric-now">Now</p>
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
                  <div className="lyric-actions">
                    <button type="button" disabled={saving} onClick={() => void stamp(line.index)}>
                      Set this line to now
                    </button>
                    {line.startSeconds != null ? (
                      <button type="button" onClick={() => playFrom(line.startSeconds ?? 0)}>
                        Play from {formatTime(line.startSeconds)}
                      </button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </>
      ) : null}
    </article>
  )
}

function FollowControls({
  timed,
  following,
  timingNote,
  saving,
  stampLabel,
  onFollow,
  onStampNext,
  onScan,
}: {
  timed: boolean
  following: boolean
  timingNote: string | null
  saving: boolean
  stampLabel: string
  onFollow: () => void
  onStampNext: () => void
  onScan: () => void
}) {
  return (
    <div className="follow">
      <button type="button" className="layer-toggle" aria-pressed={following} aria-describedby="follow-note" onClick={onFollow}>
        Follow the song
        <span className="toggle-state">{following ? 'On' : 'Off'}</span>
      </button>
      <p id="follow-note">
        {timed
          ? "Follows each line's saved start time. A scan can miss an entrance or a rest. Set this line to now when one is early or late. Scroll yourself to turn follow off."
          : 'This song has no line times yet. Scan it, or stamp each line while it plays. Scroll yourself to turn follow off.'}
      </p>
      <div className="follow-actions">
        <button type="button" disabled={saving} onClick={onStampNext}>
          Stamp next line
        </button>
        <p>Next stamp: {stampLabel}</p>
        <button type="button" disabled={saving} onClick={onScan}>
          {timed ? 'Scan again' : 'Scan line times'}
        </button>
      </div>
      {timed ? <p>Scan again replaces the saved line times.</p> : null}
      {timingNote ? <p role="status">{timingNote}</p> : null}
    </div>
  )
}

function paintLine(root: HTMLOListElement | null, index: number) {
  if (!root) return
  const previous = root.querySelector('.is-current')
  if (previous instanceof HTMLElement) {
    previous.classList.remove('is-current')
    previous.removeAttribute('aria-current')
  }
  if (index < 0) return
  const line = root.querySelector(`[data-index="${index}"]`)
  if (!(line instanceof HTMLElement)) return
  line.classList.add('is-current')
  line.setAttribute('aria-current', 'true')
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
