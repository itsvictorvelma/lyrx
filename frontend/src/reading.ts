import { useEffect, useState, type CSSProperties } from 'react'

export function useWideLayout(): boolean {
  const [wide, setWide] = useState(() => window.matchMedia('(min-width: 48rem)').matches)
  useEffect(() => {
    const query = window.matchMedia('(min-width: 48rem)')
    const update = () => setWide(query.matches)
    update()
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])
  return wide
}

export function lineRowStyle(lineCount: number): CSSProperties {
  const style: CSSProperties & Record<'--line-rows', string> = { '--line-rows': String(lineCount + 1) }
  return style
}
