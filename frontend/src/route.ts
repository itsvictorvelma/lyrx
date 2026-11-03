import { useEffect, useState } from 'react'

export type Route =
  | { name: 'library' }
  | { name: 'import' }
  | { name: 'song'; songId: string }
  | { name: 'missing' }

export function songHref(songId: string): string {
  return `/songs/${encodeURIComponent(songId)}`
}

export function parseRoute(path: string): Route {
  if (path === '/') return { name: 'library' }
  if (path === '/import') return { name: 'import' }
  const match = /^\/songs\/([^/]+)$/.exec(path)
  if (match?.[1]) return { name: 'song', songId: decodeURIComponent(match[1]) }
  return { name: 'missing' }
}

export function navigate(path: string): void {
  if (window.location.pathname === path) return
  window.history.pushState(null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function useRoute(): Route {
  const [path, setPath] = useState(() => window.location.pathname)
  useEffect(() => {
    const sync = () => setPath(window.location.pathname)
    window.addEventListener('popstate', sync)
    return () => window.removeEventListener('popstate', sync)
  }, [])
  return parseRoute(path)
}
