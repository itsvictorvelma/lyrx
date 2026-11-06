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
