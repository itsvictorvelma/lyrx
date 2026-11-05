import { useEffect, useState } from 'react'
import { listSongs } from './api.ts'
import type { SongSummary } from './contracts.ts'
import { Link } from './link.tsx'
import { filterSongs, formatDuration, languageDirection } from './rehearsal.ts'
import { songHref } from './route.ts'

export function Library({ activeId, variant = 'rail' }: { activeId?: string | null; variant?: 'page' | 'rail' }) {
  const [songs, setSongs] = useState<SongSummary[] | null>(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const page = variant === 'page'

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

  const visible = songs ? filterSongs(songs, query) : []

  return (
    <div className={page ? 'library library-page' : 'library'}>
      {page ? (
        <>
          <h1>Song Library</h1>
          <p className="lede">Ask for a song, then save it here. Original, hiragana, romaji, and English stay together.</p>
        </>
      ) : (
        <p className="rail-title">Songs</p>
      )}
      {error ? (
        <div className="notice" role="alert">
          <p>{error}</p>
          <button type="button" onClick={retry}>
            Try again
          </button>
        </div>
      ) : (
        <label className="library-search">
          Search saved songs
          <input
            type="search"
            value={query}
            autoComplete="off"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      )}
      {songs === null && !error ? <p role="status">Loading songs.</p> : null}
      {songs && songs.length === 0 ? (
        <p className="empty-note" role="status">
          No songs yet. Ask for one, then save it here.
        </p>
      ) : null}
      {songs && songs.length === 0 && page ? (
        <Link className="button-primary" href="/songs/new">
          New song
        </Link>
      ) : null}
      {songs && songs.length > 0 && visible.length === 0 ? (
        <p className="empty-note" role="status">
          No saved song matches.
        </p>
      ) : null}
      {visible.length > 0 ? (
        <ul className="song-list">
          {visible.map((song) => {
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
