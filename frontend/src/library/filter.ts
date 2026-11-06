const LANGUAGE_NAMES: Record<string, string> = {
  ja: 'Japanese',
  en: 'English',
}

function languageName(code: string): string {
  return LANGUAGE_NAMES[code] ?? code
}

export function languageDirection(source: string, target: string): string {
  return `${languageName(source)} → ${languageName(target)}`
}

export function filterSongs<T extends { title: string; artist: string }>(songs: readonly T[], query: string): T[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return [...songs]
  return songs.filter((song) => `${song.title} ${song.artist}`.toLowerCase().includes(needle))
}
