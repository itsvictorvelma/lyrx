import { useState, type FormEvent } from 'react'
import { generateLyrics, saveSong } from './api.ts'
import type { DraftLine, LyricDraft } from './contracts.ts'
import { COLUMNS } from './lyrics/columns.ts'
import { lineRowStyle, useWideLayout } from './lyrics/layout.ts'
import { LyricTabs } from './lyrics/learn.tsx'
import type { LayerKey } from './lyrics/layers.ts'
import { navigate, songHref } from './routes/route.ts'

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
    <article className={draft ? 'composer-page has-draft' : 'composer-page'}>
      {draft ? (
        <div className="draft-head">
          <div className="draft-titles">
            <h1 className="song-name" lang="ja">
              {draft.title}
            </h1>
            <p className="byline">{draft.artist}</p>
          </div>
          <button type="button" className="button-primary" disabled={pending !== null} onClick={() => void save()}>
            {pending === 'save' ? 'Saving…' : 'Save song'}
          </button>
        </div>
      ) : (
        <>
          <h1>New song</h1>
          <p className="lede">
            Ask for a song. You get Original, Hiragana, Romaji, and English here, then the recording attaches on the
            song.
          </p>
        </>
      )}
      <div className="ask-block">
        <form className="composer" onSubmit={(event) => void ask(event)}>
          <label className="composer-label" htmlFor="song-request">
            Song
          </label>
          <div className="composer-row">
            <input
              id="song-request"
              name="message"
              type="text"
              required
              maxLength={2000}
              autoComplete="off"
              placeholder="Akuma no Ko by Ai Higuchi"
              disabled={pending !== null}
            />
            <button type="submit" className="button-primary" disabled={pending !== null}>
              {pending === 'ask' ? 'Writing…' : 'Ask'}
            </button>
          </div>
        </form>
        {pending === 'ask' ? (
          <p className="ask-status" role="status">
            Writing lyrics.
          </p>
        ) : null}
        {note ? (
          <p className="ask-status" role="status">
            {note}
          </p>
        ) : null}
        {error ? (
          <p className="notice" role="alert">
            {error}
          </p>
        ) : null}
      </div>
      {draft ? (
        <div className="draft-in">
          {wide ? (
            <div className="lyric-sheet" style={lineRowStyle(draft.lines.length)}>
              {COLUMNS.map((column) => (
                <section key={column.key} className="lyric-pane" aria-labelledby={`draft-${column.key}`}>
                  <h2 className="lyric-pane-title" id={`draft-${column.key}`}>
                    {column.label}
                  </h2>
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
        <h2 className="sr-only">{column.label}</h2>
        <div className={column.className} lang={column.lang}>
          {lines.map((line, index) => (
            <p key={`${column.key}-${index}`}>{column.text(line)}</p>
          ))}
        </div>
      </section>
    </>
  )
}
