import { useEffect, useState } from 'react'
import { listSongs } from '../api.ts'
import type { SongSummary } from '../contracts.ts'
import { formatDuration } from '../player/time.ts'
import { Link } from '../routes/link.tsx'
import { songHref } from '../routes/route.ts'
import { filterSongs, languageDirection } from './filter.ts'

export function Library() {
  const [songs, setSongs] = useState<SongSummary[] | null>(null)
  const [query, setQuery] = useState('')
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

  const visible = songs ? filterSongs(songs, query) : []

  return (
    <div className="library library-page">
      <h1>Song Library</h1>
      <p className="lede">Songs you saved after a search.</p>
      <Link className="button-primary" href="/">
        Search
      </Link>
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
          No songs yet. Search for one, then save it here.
        </p>
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
            return (
              <li key={song.id}>
                <Link className="song-row" href={songHref(song.id)}>
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
