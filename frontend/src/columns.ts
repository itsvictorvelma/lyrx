import type { LyricLine } from './contracts.ts'
import type { LayerKey } from './rehearsal.ts'

export const COLUMNS: {
  key: LayerKey
  label: string
  lang: string
  className: string
  text: (
    line: Pick<LyricLine, 'originalText' | 'readingHiragana' | 'pronunciationRomaji' | 'translationEnglish'>,
  ) => string
}[] = [
  { key: 'japanese', label: 'Original', lang: 'ja', className: 'lyric-original', text: (line) => line.originalText },
  { key: 'hiragana', label: 'Hiragana', lang: 'ja', className: 'lyric-hiragana', text: (line) => line.readingHiragana },
  { key: 'romaji', label: 'Romaji', lang: 'ja-Latn', className: 'lyric-romaji', text: (line) => line.pronunciationRomaji },
  { key: 'meaning', label: 'English', lang: 'en', className: 'lyric-meaning', text: (line) => line.translationEnglish },
]
