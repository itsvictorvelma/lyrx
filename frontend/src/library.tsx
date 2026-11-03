import { useEffect, useState } from 'react'
import { listSongs } from './api.ts'
import type { SongSummary } from './contracts.ts'
import { Link } from './link.tsx'
import { formatDuration, languageDirection } from './rehearsal.ts'
import { songHref } from './route.ts'

export function Library() {
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
    <>
      <h1>Song Library</h1>
      <p className="lede">Rehearse a Japanese song with the audio, pronunciation, and direct English meaning.</p>
      {import.meta.env.DEV ? (
        <p className="dev-action">
          <Link href="/import">Import song</Link>
        </p>
      ) : null}
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
        <p role="status">{import.meta.env.DEV ? 'No songs are imported yet.' : 'No songs are available.'}</p>
      ) : null}
      {songs && songs.length > 0 ? (
        <ul className="song-list">
          {songs.map((song) => {
            const duration = formatDuration(song.durationSeconds)
            return (
              <li key={song.id}>
                <Link className="song-card" href={songHref(song.id)}>
                  <span className="song-title">{song.title}</span>
                  <span className="song-artist">{song.artist}</span>
                  <span className="song-meta">
                    {languageDirection(song.sourceLanguage, song.targetLanguage)}
                    {duration ? ` · ${duration}` : ''}
                    {song.status === 'draft' ? ' · Draft' : ''}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      ) : null}
    </>
  )
}
