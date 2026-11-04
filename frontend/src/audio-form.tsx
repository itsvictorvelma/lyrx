import { useState, type FormEvent } from 'react'
import { attachAudio } from './api.ts'

export function AudioAttach({
  songId,
  hasAudio,
  onAttached,
}: {
  songId: string
  hasAudio: boolean
  onAttached: () => void
}) {
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [replace, setReplace] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const input = event.currentTarget.elements.namedItem('audio')
    const file = input instanceof HTMLInputElement ? input.files?.[0] : undefined
    if (!file) return
    setError(null)
    setPending(true)
    try {
      await attachAudio(songId, file, hasAudio && replace)
      event.currentTarget.reset()
      setReplace(false)
      onAttached()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The audio could not be saved.')
    } finally {
      setPending(false)
    }
  }

  return (
    <form className="audio-attach" onSubmit={(event) => void submit(event)}>
      <details>
        <summary>{hasAudio ? 'Replace audio' : 'Attach audio'}</summary>
      <label>
        MP3
        <input name="audio" type="file" accept="audio/mpeg,.mp3" required />
      </label>
      {hasAudio ? (
        <label>
          <input
            name="replace"
            type="checkbox"
            checked={replace}
            onChange={(event) => setReplace(event.currentTarget.checked)}
          />{' '}
          Replace the saved audio
        </label>
      ) : null}
      {error ? (
        <p className="notice" role="alert">
          {error}
        </p>
      ) : null}
      <button type="submit" disabled={pending || (hasAudio && !replace)}>
        {pending ? 'Saving audio…' : hasAudio ? 'Replace audio' : 'Attach audio'}
      </button>
      </details>
    </form>
  )
}
