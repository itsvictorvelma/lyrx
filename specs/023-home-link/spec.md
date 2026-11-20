# 023 — Home link in the header

Status: approved (asked for by the user on 2026-11-20)

## Goal

Getting back to the home page is obvious from every page. Today only the `lyrx` wordmark goes home, and newcomers don't expect that.

## In scope

- A "Home" link in the header, before "Your songs", on every page.

## Out of scope

- Changing the song page's back arrow (it still goes to Your songs).

## Rules

- "Home" goes to `/`. The link for the page you are on has `aria-current="page"` and is shown by weight and a tint, never colour alone (the existing `.nav-link` style).
- The wordmark still goes home too.

## Security

- No new input; a fixed same-site link.

## Acceptance checks

- AC-1: On every page the header has Home and Your songs. Home goes to `/` and is marked current there; Your songs is marked current on `/library`; on a song page neither is.

## Plan

- `header/Header.tsx`: the Home link; `isLibraryPage` becomes `currentPage` (`Route["page"]`). `App.tsx` passes it.
- Test in `home/HomePage.test.tsx`.
