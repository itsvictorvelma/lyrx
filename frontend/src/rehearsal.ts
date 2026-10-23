import type { LyricLine } from './contracts.ts'

export const LAYER_STORAGE_KEY = 'lyrx.layers.v1'
export const FOLLOW_STORAGE_KEY = 'lyrx.follow.v1'

export type LayerKey = 'japanese' | 'romaji' | 'meaning'

export type LayerVisibility = Record<LayerKey, boolean>

export type KeyValueStore = {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

export type LyricProblem = 'empty' | 'index' | 'id' | 'text'

const LANGUAGE_NAMES: Record<string, string> = {
  ja: 'Japanese',
  en: 'English',
}

export const ALL_LAYERS: LayerVisibility = {
  japanese: true,
  romaji: true,
  meaning: true,
}

export function languageName(code: string): string {
  return LANGUAGE_NAMES[code] ?? code
}

export function languageDirection(source: string, target: string): string {
  return `${languageName(source)} → ${languageName(target)}`
}

export function formatTime(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return '--:--'
  const total = Math.floor(seconds)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  const ss = String(secs).padStart(2, '0')
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${ss}`
  return `${minutes}:${ss}`
}

export function formatDuration(seconds: number | null | undefined): string | null {
  const text = formatTime(seconds)
  return text === '--:--' ? null : text
}

export function finiteTime(value: number): number | null {
  if (!Number.isFinite(value) || value < 0) return null
  return value
}

export function clampTime(value: number, duration: number): number {
  const length = finiteTime(duration)
  if (length == null) return 0
  if (!Number.isFinite(value)) return 0
  return Math.min(length, Math.max(0, value))
}

export function playbackRate(value: number): 0.75 | 1 | 1.25 | null {
  if (value === 0.75 || value === 1 || value === 1.25) return value
  return null
}

export function visibleLayerCount(layers: LayerVisibility): number {
  return Number(layers.japanese) + Number(layers.romaji) + Number(layers.meaning)
}

export function readLayers(storage: KeyValueStore | null): LayerVisibility {
  if (!storage) return { ...ALL_LAYERS }
  try {
    const raw = storage.getItem(LAYER_STORAGE_KEY)
    if (!raw) return { ...ALL_LAYERS }
    const parsed: unknown = JSON.parse(raw)
    if (!isLayerVisibility(parsed)) return { ...ALL_LAYERS }
    if (visibleLayerCount(parsed) === 0) return { ...ALL_LAYERS }
    return parsed
  } catch {
    return { ...ALL_LAYERS }
  }
}

export function writeLayers(storage: KeyValueStore, value: LayerVisibility): void {
  try {
    storage.setItem(LAYER_STORAGE_KEY, JSON.stringify(value))
  } catch {
    // sessionStorage can be blocked. The on-screen choice still applies until reload.
  }
}

export function toggleLayer(current: LayerVisibility, key: LayerKey): LayerVisibility | null {
  const next = { ...current, [key]: !current[key] }
  if (visibleLayerCount(next) === 0) return null
  return next
}

export function readFollow(storage: KeyValueStore | null): boolean {
  if (!storage) return true
  try {
    const value = storage.getItem(FOLLOW_STORAGE_KEY)
    if (value === '0') return false
    return true
  } catch {
    return true
  }
}

export function writeFollow(storage: KeyValueStore, following: boolean): void {
  try {
    storage.setItem(FOLLOW_STORAGE_KEY, following ? '1' : '0')
  } catch {
    // sessionStorage can be blocked. The on-screen choice still applies until reload.
  }
}

export function readLineStarts(lines: readonly { startSeconds?: number | null }[]): (number | null)[] {
  return lines.map((line) => {
    const start = line.startSeconds
    if (typeof start !== 'number' || !Number.isFinite(start) || start < 0) return null
    return start
  })
}

export function hasLineTime(starts: readonly (number | null)[]): boolean {
  return starts.some((start) => start != null)
}

export function activeLineIndex(current: number, starts: readonly (number | null)[]): number | null {
  if (!Number.isFinite(current) || current < 0) return null
  let best: number | null = null
  for (let index = 0; index < starts.length; index += 1) {
    const start = starts[index]
    if (start == null || start > current) continue
    if (best == null || start >= (starts[best] ?? -1)) best = index
  }
  return best
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

function isLayerVisibility(value: unknown): value is LayerVisibility {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  const keys = Object.keys(record)
  if (keys.length !== 3) return false
  return keys.every((key) => (key === 'japanese' || key === 'romaji' || key === 'meaning') && typeof record[key] === 'boolean')
}
