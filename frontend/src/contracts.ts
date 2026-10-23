// Same data shapes as backend/app/contracts.py.
// Line numbers start at 0. Do not add timing fields.
// Change both files in the same commit.

export type SongStatus = 'draft' | 'published'

export type SongSummary = {
  id: string
  title: string
  artist: string
  sourceLanguage: string
  targetLanguage: string
  durationSeconds?: number
  status: SongStatus
}

export type LyricLine = {
  id: string
  index: number
  originalText: string
  pronunciationRomaji: string
  translationEnglish: string
}

export type SongDetail = SongSummary & {
  audioUrl: string
  contentVersion: string
  lines: LyricLine[]
}

export type ErrorDetail = {
  field?: string
  file?: string
  line?: number
}

export type ErrorResponse = {
  code: string
  message: string
  details?: ErrorDetail[]
  requestId?: string
}
