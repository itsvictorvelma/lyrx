import type { ReactNode } from 'react'
import { navigate } from './route.ts'

export function Link({
  href,
  className,
  children,
  current = false,
}: {
  href: string
  className?: string
  children: ReactNode
  current?: boolean
}) {
  return (
    <a
      className={className}
      href={href}
      aria-current={current ? 'page' : undefined}
      onClick={(event) => {
        if (
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        ) {
          return
        }
        event.preventDefault()
        navigate(href)
      }}
    >
      {children}
    </a>
  )
}
