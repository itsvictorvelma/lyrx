import { useEffect, useState, type FormEvent } from 'react'
import { apiBaseUrl, errorMessage, getSong, listSongs } from './api.ts'
import type { SongDetail, SongSummary } from './contracts.ts'

export default function App() {
  const [songs, setSongs] = useState<SongSummary[]>([])
  const [selected, setSelected] = useState<SongDetail | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadSongs() {
    setError(null)
    try {
      setSongs(await listSongs())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The song list could not be loaded.')
    }
  }

  async function openSong(songId: string) {
    setError(null)
    try {
      setSelected(await getSong(songId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The song could not be loaded.')
    }
  }

  useEffect(() => {
    let active = true
    listSongs()
      .then((next) => {
        if (active) {
          setSongs(next)
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : 'The song list could not be loaded.')
        }
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <main>
      <h1>Lyrx</h1>
      <p>Rehearse a Japanese song with the audio, pronunciation, and direct English meaning.</p>
      {import.meta.env.DEV ? (
        <ImportForm
          onImported={(song) => {
            setSelected(song)
            setMessage(`${song.title} is saved.`)
            void loadSongs()
          }}
        />
      ) : null}
      <section aria-labelledby="library-heading">
        <h2 id="library-heading">Song Library</h2>
        {error ? <p role="alert">{error}</p> : null}
        {message ? <p role="status">{message}</p> : null}
        {songs.length === 0 ? <p>No songs yet.</p> : null}
        <ul>
          {songs.map((song) => (
            <li key={song.id}>
              <button type="button" onClick={() => void openSong(song.id)}>
                {song.title} by {song.artist}
              </button>
            </li>
          ))}
        </ul>
      </section>
      {selected ? <SongView song={selected} /> : null}
    </main>
  )
}

function ImportForm({ onImported }: { onImported: (song: SongDetail) => void }) {
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setPending(true)
    const form = event.currentTarget
    const body = new FormData(form)
    try {
      const response = await fetch(`${apiBaseUrl}/api/import`, { method: 'POST', body })
      if (!response.ok) {
        throw new Error(await errorMessage(response))
      }
      onImported((await response.json()) as SongDetail)
      form.reset()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The import failed.')
    } finally {
      setPending(false)
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)}>
      <h2>Import Song</h2>
      <p>Development only. Each file must use the exact name shown on its field.</p>
      <label>
        Song id
        <input name="songId" required pattern="[a-z0-9]+(-[a-z0-9]+)*" autoComplete="off" />
      </label>
      <label>
        Title
        <input name="title" required />
      </label>
      <label>
        Artist
        <input name="artist" required />
      </label>
      <label>
        Source language
        <input name="sourceLanguage" required defaultValue="ja" />
      </label>
      <label>
        Target language
        <input name="targetLanguage" required defaultValue="en" />
      </label>
      <label>
        Japanese lyrics, named original.txt
        <input name="original" type="file" accept=".txt,text/plain" required />
      </label>
      <label>
        Pronunciation, named pronunciation.txt
        <input name="pronunciation" type="file" accept=".txt,text/plain" required />
      </label>
      <label>
        Direct meaning, named translation.txt
        <input name="translation" type="file" accept=".txt,text/plain" required />
      </label>
      <label>
        Audio, named audio.mp3
        <input name="audio" type="file" accept="audio/mpeg,.mp3" required />
      </label>
      <label>
        <input name="replace" type="checkbox" value="true" /> Replace an existing song with this id
      </label>
      {error ? <p role="alert">{error}</p> : null}
      <button type="submit" disabled={pending}>
        {pending ? 'Importing…' : 'Import song'}
      </button>
    </form>
  )
}

function SongView({ song }: { song: SongDetail }) {
  return (
    <section aria-labelledby="song-heading">
      <h2 id="song-heading">{song.title}</h2>
      <p>{song.artist}</p>
      <audio controls src={song.audioUrl}>
        Audio
      </audio>
      <ol>
        {song.lines.map((line) => (
          <li key={line.id} className="lyric">
            <p className="layer" lang="ja">
              <span>Japanese</span>
              {line.originalText}
            </p>
            <p className="layer">
              <span>Pronunciation (Romaji)</span>
              {line.pronunciationRomaji}
            </p>
            <p className="layer" lang="en">
              <span>Direct Meaning</span>
              {line.translationEnglish}
            </p>
          </li>
        ))}
      </ol>
    </section>
  )
}
