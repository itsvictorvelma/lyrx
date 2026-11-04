import { useEffect, useState } from 'react'
import { listSongs } from './api.ts'
import type { SongSummary } from './contracts.ts'
import { Link } from './link.tsx'
import { formatDuration, languageDirection } from './rehearsal.ts'
import { songHref } from './route.ts'

export function Library({ activeId }: { activeId?: string | null }) {
  const [songs, setSongs] = useState<SongSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    listSongs()
      .then((next) => {
        if (!active) return
        setSongs(next)
        setError(null)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason.message : 'The song list could not be loaded.')
      })
    return () => {
      active = false
    }
  }, [attempt])

  function retry() {
    setSongs(null)
    setError(null)
    setAttempt((value) => value + 1)
  }

  return (
    <div className="library">
      <h1 className="rail-title">Songs</h1>
      {songs === null && !error ? <p role="status">Loading songs.</p> : null}
      {error ? (
        <div className="notice" role="alert">
          <p>{error}</p>
          <button type="button" onClick={retry}>
            Try again
          </button>
        </div>
      ) : null}
      {songs && songs.length === 0 ? (
        <p className="empty-note" role="status">
          No songs yet.
        </p>
      ) : null}
      {songs && songs.length > 0 ? (
        <ul className="song-list">
          {songs.map((song) => {
            const duration = formatDuration(song.durationSeconds)
            const current = song.id === activeId
            return (
              <li key={song.id}>
                <Link className="song-row" href={songHref(song.id)} current={current}>
                  <span className="song-mark" aria-hidden="true">
                    {monogram(song.title)}
                  </span>
                  <span className="song-copy">
                    <span className="song-title">{song.title}</span>
                    <span className="song-artist">{song.artist}</span>
                    <span className="song-meta">
                      {languageDirection(song.sourceLanguage, song.targetLanguage)}
                      {duration ? ` · ${duration}` : ''}
                      {song.status === 'draft' ? ' · Draft' : ''}
                    </span>
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      ) : null}
    </div>
  )
}

function monogram(title: string): string {
  return Array.from(title.trim())[0] ?? '·'
}
