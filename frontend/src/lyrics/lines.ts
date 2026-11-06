import type { LyricLine } from '../contracts.ts'

export type LyricProblem = 'empty' | 'index' | 'id' | 'text'

export function lineIndexFromValue(value: string | null | undefined): number | null {
  if (value == null || !/^\d+$/.test(value)) return null
  return Number(value)
}

export function linkedLineIndex(
  hoverIndex: number | null,
  focusIndex: number | null,
  visibleDocuments: number,
): number | null {
  if (visibleDocuments < 2) return null
  if (hoverIndex != null) return hoverIndex
  return focusIndex
}

export function lyricProblem(lines: LyricLine[]): LyricProblem | null {
  if (lines.length === 0) return 'empty'
  const ids = new Set<string>()
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    if (!line || line.index !== index) return 'index'
    if (!line.id || ids.has(line.id)) return 'id'
    ids.add(line.id)
    if (!line.originalText.trim() || !line.pronunciationRomaji.trim() || !line.translationEnglish.trim()) {
      return 'text'
    }
  }
  return null
}
