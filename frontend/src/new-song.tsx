import { useState, type FormEvent } from 'react'
import { generateLyrics, saveSong } from './api.ts'
import type { DraftLine, LyricDraft, LyricLine } from './contracts.ts'
import { COLUMNS } from './lyrics/columns.ts'
import { DesktopLyrics, LayerToggle, LyricDocument, LyricTabs } from './lyrics/learn.tsx'
import { readLayers, toggleLayer, writeLayers, type LayerKey, type LayerVisibility } from './lyrics/layers.ts'
import { useWideLayout } from './lyrics/layout.ts'
import { navigate, songHref } from './routes/route.ts'

export function NewSong() {
  const [draft, setDraft] = useState<LyricDraft | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<'send' | 'save' | null>(null)
  const [reading, setReading] = useState<LayerKey>('japanese')
  const [layers, setLayers] = useState<LayerVisibility>(() => readLayers(browserLayers()))
  const wide = useWideLayout()

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = new FormData(event.currentTarget).get('message')
    if (typeof message !== 'string' || !message.trim()) return
    setError(null)
    setPending('send')
    try {
      const result = await generateLyrics(message.trim())
      setDraft(result.draft)
      setNote(result.message)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The lyrics could not be written.')
    } finally {
      setPending(null)
    }
  }

  async function save() {
    if (!draft) return
    setError(null)
    setPending('save')
    try {
      const song = await saveSong(draft)
      navigate(songHref(song.id))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The song could not be saved.')
      setPending(null)
    }
  }

  function changeLayer(key: LayerKey) {
    const next = toggleLayer(layers, key)
    setLayers(next)
    const storage = browserLayers()
    if (storage) writeLayers(storage, next)
  }

  const lines = draft ? readable(draft.lines) : []
  const column = COLUMNS.find((item) => item.key === reading) ?? COLUMNS[0]

  return (
    <article className="composer-page">
      <h1>Search</h1>
      <p className="lede">Type a song name. You get Original, Hiragana, Romaji, and English.</p>
      <form className="composer" onSubmit={(event) => void send(event)}>
        <label>
          Song
          <input name="message" required autoComplete="off" placeholder="Akuma no Ko by Ai Higuchi" />
        </label>
        <button type="submit" className="button-primary" disabled={pending !== null}>
          {pending === 'send' ? 'Sending…' : 'Send'}
        </button>
      </form>
      {pending === 'send' ? <p role="status">Searching.</p> : null}
      {note ? <p role="status">{note}</p> : null}
      {error ? (
        <p className="notice" role="alert">
          {error}
        </p>
      ) : null}
      {draft ? (
        <div className="draft-in learn">
          <h2>
            {draft.title} <span className="byline">{draft.artist}</span>
          </h2>
          {wide ? (
            <DesktopLyrics lines={lines} layers={layers} onToggle={changeLayer} />
          ) : (
            <>
              <div className="lyric-switch">
                <LyricTabs active={column.key} onSelect={setReading} />
                <LayerToggle label={column.label} shown={layers[column.key]} onToggle={() => changeLayer(column.key)} />
              </div>
              <LyricDocument
                column={column}
                lines={lines}
                labelledBy={`tab-${column.key}`}
                shown={layers[column.key]}
              />
            </>
          )}
          <button type="button" className="button-primary" disabled={pending !== null} onClick={() => void save()}>
            {pending === 'save' ? 'Saving…' : 'Save song'}
          </button>
        </div>
      ) : null}
    </article>
  )
}

function readable(lines: DraftLine[]): LyricLine[] {
  return lines.map((line, index) => ({
    id: `draft-${index}`,
    index,
    originalText: line.originalText,
    readingHiragana: line.readingHiragana,
    pronunciationRomaji: line.pronunciationRomaji,
    translationEnglish: line.translationEnglish,
  }))
}

function browserLayers(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}
