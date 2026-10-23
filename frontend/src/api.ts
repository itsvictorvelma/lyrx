import type { ErrorResponse, SongDetail, SongSummary } from './contracts.ts'

export const apiBaseUrl = 'http://localhost:8000'

export async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ErrorResponse
    return body.message
  } catch {
    return 'The request failed.'
  }
}

export async function listSongs(): Promise<SongSummary[]> {
  const response = await fetch(`${apiBaseUrl}/api/songs`)
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return (await response.json()) as SongSummary[]
}

export async function getSong(songId: string): Promise<SongDetail> {
  const response = await fetch(`${apiBaseUrl}/api/songs/${songId}`)
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return (await response.json()) as SongDetail
}
