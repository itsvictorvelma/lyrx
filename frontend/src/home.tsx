import { Link } from './link.tsx'

const SAMPLE = [
  { label: 'Original', lang: 'ja', className: 'lyric-original', text: '雨が降る' },
  { label: 'Hiragana', lang: 'ja', className: 'lyric-hiragana', text: 'あめがふる' },
  { label: 'Romaji', lang: 'ja-Latn', className: 'lyric-romaji', text: 'ame ga furu' },
  { label: 'English', lang: 'en', className: 'lyric-meaning', text: 'Rain is falling' },
] as const

export function Home() {
  return (
    <article className="home">
      <p className="eyebrow">Japanese rehearsal</p>
      <h1>One song, read four ways.</h1>
      <p className="lede">
        Original, hiragana, romaji, and the direct English meaning, with the recording kept beside the words.
      </p>
      <div className="home-actions">
        <Link className="button-primary" href="/songs">
          Song library
        </Link>
        <Link className="button-ghost" href="/search">
          Search for a song
        </Link>
      </div>
      <figure className="sample">
        <figcaption>A line, shown together</figcaption>
        <div className="sample-grid">
          {SAMPLE.map((column) => (
            <div key={column.label}>
              <span className="sample-label">{column.label}</span>
              <p className={column.className} lang={column.lang}>
                {column.text}
              </p>
            </div>
          ))}
        </div>
      </figure>
    </article>
  )
}
