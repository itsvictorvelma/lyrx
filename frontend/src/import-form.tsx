import { useState, type FormEvent } from 'react'
import { apiBaseUrl, errorMessage } from './api.ts'
import type { SongDetail } from './contracts.ts'
import { Link } from './link.tsx'
import { navigate, songHref } from './route.ts'

export function ImportPage() {
  if (!import.meta.env.DEV) {
    return (
      <>
        <h1>Import Song</h1>
        <p>Import is only available in development.</p>
        <p>
          <Link href="/">Song Library</Link>
        </p>
      </>
    )
  }

  return (
    <>
      <h1>Import Song</h1>
      <p className="lede">Development only. Each file must use the exact name shown on its field.</p>
      <ImportForm onImported={(song) => navigate(songHref(song.id))} />
      <p className="dev-action">
        <Link href="/">Song Library</Link>
      </p>
    </>
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
      if (!response.ok) throw new Error(await errorMessage(response))
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
        <input name="replace" type="checkbox" value="true" /> Replace the saved song with this title
      </label>
      {error ? (
        <p className="notice" role="alert">
          {error}
        </p>
      ) : null}
      {pending ? (
        <p role="status">Importing and scanning the song for line times. The first scan can take a few minutes.</p>
      ) : null}
      <button type="submit" className="button-primary" disabled={pending}>
        {pending ? 'Importing…' : 'Import song'}
      </button>
    </form>
  )
}
