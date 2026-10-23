import type { LyricLine } from './contracts.ts'

export const LAYER_STORAGE_KEY = 'lyrx.layers.v1'
export const FOLLOW_STORAGE_KEY = 'lyrx.follow.v1'
export const PACE_STORAGE_KEY = 'lyrx.pace.v1'

// The first imported song starts singing here. Other songs do not use this number.
export const FIRST_SONG_ID = 'akuma-no-ko'
export const FIRST_SONG_INTRO_SECONDS = 5.5

export type SongPace = {
  introSeconds: number
  secondsPerLine: number | null
}

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

export function defaultIntroSeconds(songId: string): number {
  return songId === FIRST_SONG_ID ? FIRST_SONG_INTRO_SECONDS : 0
}

export function defaultSecondsPerLine(duration: number, lineCount: number, introSeconds: number): number | null {
  if (!Number.isFinite(duration) || !Number.isFinite(introSeconds) || !Number.isFinite(lineCount) || lineCount < 1) {
    return null
  }
  const singing = duration - introSeconds
  if (singing <= 0) return null
  return singing / lineCount
}

export function secondsPerLineFromBpm(bpm: number, beatsPerLine: number): number | null {
  if (!Number.isFinite(bpm) || bpm < 40 || bpm > 300) return null
  if (!Number.isFinite(beatsPerLine) || beatsPerLine <= 0 || beatsPerLine > 32) return null
  return (60 / bpm) * beatsPerLine
}

export function singingLineIndex(
  current: number,
  introSeconds: number,
  secondsPerLine: number,
  lineCount: number,
): number | null {
  if (!Number.isFinite(current) || !Number.isFinite(introSeconds) || introSeconds < 0) return null
  if (!Number.isFinite(secondsPerLine) || secondsPerLine <= 0) return null
  if (!Number.isInteger(lineCount) || lineCount < 1) return null
  if (current <= introSeconds) return 0
  return Math.min(lineCount - 1, Math.floor((current - introSeconds) / secondsPerLine))
}

export function readPace(storage: KeyValueStore | null, songId: string): SongPace {
  const fallback: SongPace = { introSeconds: defaultIntroSeconds(songId), secondsPerLine: null }
  if (!storage) return fallback
  try {
    const raw = storage.getItem(PACE_STORAGE_KEY)
    if (!raw) return fallback
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return fallback
    const entry = (parsed as Record<string, unknown>)[songId]
    if (!isPace(entry)) return fallback
    return entry
  } catch {
    return fallback
  }
}

export function writePace(storage: KeyValueStore, songId: string, pace: SongPace): void {
  try {
    const raw = storage.getItem(PACE_STORAGE_KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : {}
    const map = parsed && typeof parsed === 'object' ? { ...(parsed as Record<string, unknown>) } : {}
    map[songId] = pace
    storage.setItem(PACE_STORAGE_KEY, JSON.stringify(map))
  } catch {
    // localStorage can be blocked. The on-screen choice still applies until reload.
  }
}

function isPace(value: unknown): value is SongPace {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  const intro = record.introSeconds
  const seconds = record.secondsPerLine
  const introOk = typeof intro === 'number' && intro >= 0 && intro < 600
  const secondsOk = seconds === null || (typeof seconds === 'number' && seconds > 0 && seconds <= 30)
  return introOk && secondsOk
}

export function followScrollTop(progress: number, start: number, end: number): number | null {
  if (!Number.isFinite(progress) || progress < 0) return null
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return null
  const bounded = Math.min(1, progress)
  return start + bounded * (end - start)
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
