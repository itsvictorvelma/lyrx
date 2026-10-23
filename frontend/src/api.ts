import type { ErrorResponse, SongDetail, SongSummary } from './contracts.ts'

export const apiBaseUrl = 'http://localhost:8000'

export class ApiFailure extends Error {
  readonly status: number
  readonly code: string | null

  constructor(message: string, status: number, code: string | null) {
    super(message)
    this.name = 'ApiFailure'
    this.status = status
    this.code = code
  }
}

export async function errorMessage(response: Response): Promise<string> {
  return (await readFailure(response)).message
}

export async function listSongs(): Promise<SongSummary[]> {
  const response = await fetch(`${apiBaseUrl}/api/songs`)
  if (!response.ok) throw await readFailure(response)
  return (await response.json()) as SongSummary[]
}

export async function getSong(songId: string): Promise<SongDetail> {
  const response = await fetch(`${apiBaseUrl}/api/songs/${encodeURIComponent(songId)}`)
  if (!response.ok) throw await readFailure(response)
  return (await response.json()) as SongDetail
}

async function readFailure(response: Response): Promise<ApiFailure> {
  try {
    const body = (await response.json()) as ErrorResponse
    return new ApiFailure(body.message || 'The request failed.', response.status, body.code ?? null)
  } catch {
    return new ApiFailure('The request failed.', response.status, null)
  }
}
