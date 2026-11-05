import { useState, type FormEvent } from 'react'
import { generateLyrics, saveSong } from './api.ts'
import type { DraftLine, LyricDraft } from './contracts.ts'
import { COLUMNS } from './columns.ts'
import { LyricTabs } from './learn.tsx'
import { lineRowStyle, useWideLayout } from './reading.ts'
import { Link } from './link.tsx'
import { navigate, songHref } from './route.ts'
import type { LayerKey } from './rehearsal.ts'

export function NewSong() {
  const [draft, setDraft] = useState<LyricDraft | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<'ask' | 'save' | null>(null)
  const [reading, setReading] = useState<LayerKey>('japanese')
  const wide = useWideLayout()

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = new FormData(event.currentTarget).get('message')
    if (typeof message !== 'string' || !message.trim()) return
    setError(null)
    setPending('ask')
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

  return (
    <article className="composer-page">
      <Link className="back-link" href="/">
        Songs
      </Link>
      <h1>New song</h1>
      <p className="lede">Ask for a song. You get Original, Hiragana, Romaji, and English here, then the recording attaches on the song.</p>
      <form className="composer" onSubmit={(event) => void ask(event)}>
        <label>
          Song
          <textarea name="message" required rows={3} placeholder="Akuma no Ko by Ai Higuchi" />
        </label>
        <button type="submit" className="button-primary" disabled={pending !== null}>
          {pending === 'ask' ? 'Writing lyrics…' : 'Ask'}
        </button>
      </form>
      {pending === 'ask' ? <p role="status">Writing lyrics.</p> : null}
      {note ? <p role="status">{note}</p> : null}
      {error ? (
        <p className="notice" role="alert">
          {error}
        </p>
      ) : null}
      {draft ? (
        <div className="draft-in">
          <h2>
            {draft.title} <span className="byline">{draft.artist}</span>
          </h2>
          {wide ? (
            <div className="lyric-sheet" style={lineRowStyle(draft.lines.length)}>
              {COLUMNS.map((column) => (
                <section key={column.key} className="lyric-pane" aria-labelledby={`draft-${column.key}`}>
                  <h3 className="lyric-pane-title" id={`draft-${column.key}`}>
                    {column.label}
                  </h3>
                  <div className={`lyric-body ${column.className}`} lang={column.lang}>
                    {draft.lines.map((line, index) => (
                      <p key={`${column.key}-${index}`}>{column.text(line)}</p>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <DraftTabs lines={draft.lines} reading={reading} onSelect={setReading} />
          )}
          <button type="button" className="button-primary" disabled={pending !== null} onClick={() => void save()}>
            {pending === 'save' ? 'Saving…' : 'Save song'}
          </button>
        </div>
      ) : null}
    </article>
  )
}

function DraftTabs({
  lines,
  reading,
  onSelect,
}: {
  lines: DraftLine[]
  reading: LayerKey
  onSelect: (key: LayerKey) => void
}) {
  const column = COLUMNS.find((item) => item.key === reading) ?? COLUMNS[0]
  return (
    <>
      <div className="lyric-switch">
        <LyricTabs active={column.key} onSelect={onSelect} />
      </div>
      <section
        key={column.key}
        className="lyric-document"
        id={`panel-${column.key}`}
        role="tabpanel"
        aria-labelledby={`tab-${column.key}`}
      >
        <h3 className="sr-only">{column.label}</h3>
        <div className={column.className} lang={column.lang}>
          {lines.map((line, index) => (
            <p key={`${column.key}-${index}`}>{column.text(line)}</p>
          ))}
        </div>
      </section>
    </>
  )
}
