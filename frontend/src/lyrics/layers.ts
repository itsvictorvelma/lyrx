export const LAYER_STORAGE_KEY = 'lyrx.layers.v2'

export type LayerKey = 'japanese' | 'hiragana' | 'romaji' | 'meaning'

export type LayerVisibility = Record<LayerKey, boolean>

export type KeyValueStore = {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

export const ALL_LAYERS: LayerVisibility = {
  japanese: true,
  hiragana: true,
  romaji: true,
  meaning: true,
}

export function readLayers(storage: KeyValueStore | null): LayerVisibility {
  if (!storage) return { ...ALL_LAYERS }
  try {
    const raw = storage.getItem(LAYER_STORAGE_KEY)
    if (!raw) return { ...ALL_LAYERS }
    const parsed: unknown = JSON.parse(raw)
    if (!isLayerVisibility(parsed)) return { ...ALL_LAYERS }
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

export function toggleLayer(current: LayerVisibility, key: LayerKey): LayerVisibility {
  return { ...current, [key]: !current[key] }
}

function isLayerVisibility(value: unknown): value is LayerVisibility {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  const keys = Object.keys(record)
  if (keys.length !== 4) return false
  return keys.every(
    (key) =>
      (key === 'japanese' || key === 'hiragana' || key === 'romaji' || key === 'meaning') &&
      typeof record[key] === 'boolean',
  )
}
