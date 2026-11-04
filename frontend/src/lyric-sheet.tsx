import type { ReactNode } from 'react'
import { COLUMNS } from './columns.ts'
import type { LyricLine } from './contracts.ts'
import type { LayerKey, LayerVisibility } from './rehearsal.ts'

type SheetLine = Pick<LyricLine, 'originalText' | 'readingHiragana' | 'pronunciationRomaji' | 'translationEnglish'> & {
  id?: string
}

export function LyricSheet({
  lines,
  layers,
  heading,
  idPrefix,
  toggle,
}: {
  lines: SheetLine[]
  layers?: LayerVisibility
  heading: 'h2' | 'h3'
  idPrefix: string
  toggle?: (label: string, shown: boolean, key: LayerKey) => ReactNode
}) {
  const Title = heading
  return (
    <div className="lyric-sheet">
      {COLUMNS.map((column) => {
        const shown = layers?.[column.key] ?? true
        return (
          <header key={column.key} className="lyric-pane-title">
            <Title id={`${idPrefix}-${column.key}`}>{column.label}</Title>
            {toggle ? toggle(column.label, shown, column.key) : null}
          </header>
        )
      })}
      {lines.map((line, index) =>
        COLUMNS.map((column) => {
          const shown = layers?.[column.key] ?? true
          const empty = lines.every((row) => column.text(row).trim() === '')
          const text = empty && index === 0 ? '' : column.text(line)
          return (
            <div
              key={`${line.id ?? index}-${column.key}`}
              className={shown ? column.className : `${column.className} is-hidden`}
              lang={column.lang}
              aria-labelledby={`${idPrefix}-${column.key}`}
              aria-hidden={shown ? undefined : true}
            >
              {empty && index === 0 ? <p className="lyric-empty">Nothing here yet.</p> : <p>{text}</p>}
            </div>
          )
        }),
      )}
    </div>
  )
}
