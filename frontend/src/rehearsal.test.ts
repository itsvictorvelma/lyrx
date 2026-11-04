import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import type { LyricLine } from './contracts.ts'
import { parseRoute, songHref } from './route.ts'
import {
  ALL_LAYERS,
  LAYER_STORAGE_KEY,
  clampTime,
  formatTime,
  languageDirection,
  lineIndexFromValue,
  linkedLineIndex,
  lyricProblem,
  playbackRate,
  readLayers,
  toggleLayer,
  writeLayers,
  type KeyValueStore,
} from './rehearsal.ts'

function memory(initial?: Record<string, string>): KeyValueStore & { values: Map<string, string> } {
  const values = new Map(Object.entries(initial ?? {}))
  return {
    values,
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  }
}

function line(index: number, id = `line-${index}`): LyricLine {
  return {
    id,
    index,
    originalText: 'あ',
    readingHiragana: 'あ',
    pronunciationRomaji: 'a',
    translationEnglish: 'ah',
  }
}

test('formatTime uses m:ss until one hour, then h:mm:ss', () => {
  assert.equal(formatTime(0), '0:00')
  assert.equal(formatTime(65), '1:05')
  assert.equal(formatTime(222), '3:42')
  assert.equal(formatTime(3600), '1:00:00')
  assert.equal(formatTime(3661), '1:01:01')
  assert.equal(formatTime(null), '--:--')
  assert.equal(formatTime(Number.NaN), '--:--')
  assert.equal(formatTime(Number.POSITIVE_INFINITY), '--:--')
  assert.equal(formatTime(-1), '--:--')
})

test('clampTime stays inside the track', () => {
  assert.equal(clampTime(-4, 20), 0)
  assert.equal(clampTime(12, 20), 12)
  assert.equal(clampTime(25, 20), 20)
  assert.equal(clampTime(Number.NaN, 20), 0)
  assert.equal(clampTime(4, Number.NaN), 0)
})

test('playbackRate allows only the three rehearsal speeds', () => {
  assert.equal(playbackRate(0.75), 0.75)
  assert.equal(playbackRate(1), 1)
  assert.equal(playbackRate(1.25), 1.25)
  assert.equal(playbackRate(1.5), null)
  assert.equal(playbackRate(2), null)
})

test('layer storage falls back when missing or invalid, and keeps an all-hidden choice', () => {
  assert.deepEqual(readLayers(null), ALL_LAYERS)
  assert.deepEqual(readLayers(memory()), ALL_LAYERS)
  assert.deepEqual(readLayers(memory({ [LAYER_STORAGE_KEY]: '{no' })), ALL_LAYERS)
  assert.deepEqual(readLayers(memory({ [LAYER_STORAGE_KEY]: '{"japanese":false}' })), ALL_LAYERS)
  const none = { japanese: false, hiragana: false, romaji: false, meaning: false }
  assert.deepEqual(readLayers(memory({ [LAYER_STORAGE_KEY]: JSON.stringify(none) })), none)
  assert.deepEqual(
    readLayers(memory({ [LAYER_STORAGE_KEY]: '{"japanese":false,"hiragana":true,"romaji":true,"meaning":true}' })),
    { japanese: false, hiragana: true, romaji: true, meaning: true },
  )
})

test('a lyric mark follows one line and the same index, without stretching the row', () => {
  assert.equal(lineIndexFromValue('0'), 0)
  assert.equal(lineIndexFromValue('12'), 12)
  assert.equal(lineIndexFromValue(null), null)
  assert.equal(lineIndexFromValue(''), null)
  assert.equal(lineIndexFromValue('1.5'), null)
  assert.equal(lineIndexFromValue('-1'), null)
  assert.equal(linkedLineIndex(2, 0, 4), 2)
  assert.equal(linkedLineIndex(null, 0, 4), 0)
  assert.equal(linkedLineIndex(null, null, 4), null)
  assert.equal(linkedLineIndex(1, 0, 1), null)
  assert.equal(linkedLineIndex(1, null, 0), null)

  const here = dirname(fileURLToPath(import.meta.url))
  const css = readFileSync(join(here, 'index.css'), 'utf8')
  const learn = readFileSync(join(here, 'learn.tsx'), 'utf8')
  const sheet = ruleBody(css, '.lyric-sheet')
  const linked = ruleBody(css, '.learn .lyric-line.is-linked')
  assert.match(sheet, /display:\s*flex/)
  assert.doesNotMatch(css, /subgrid|lyric-sheet-aligned|grid-template-rows|1\.375rem/)
  const documents = ruleBody(
    css,
    '.lyric-original,\n.lyric-hiragana,\n.lyric-romaji,\n.lyric-meaning',
  )
  assert.match(documents, /font-size:\s*var\(--text-reading\)/)
  assert.match(documents, /line-height:\s*1\.65/)
  assert.match(css, /font-size:\s*1rem;\s*line-height:\s*1\.65/)
  assert.match(linked, /background-color:\s*var\(--line\)/)
  assert.match(linked, /text-decoration-line:\s*underline/)
  assert.doesNotMatch(linked, /margin|padding|min-height|height|grid|font-size|font-weight|width|transform|letter-spacing|transition/)
  assert.doesNotMatch(learn, /alignedRowTracks|gridTemplateRows|subgrid|lyric-sheet-aligned/)
  assert.match(learn, /linkedLineIndex\(/)
  assert.match(learn, /is-linked/)
  assert.match(learn, /data-line/)
  assert.match(learn, /tabIndex=\{shown \? 0 : undefined\}/)
})

function ruleBody(css: string, selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = css.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `missing ${selector}`)
  return match[1] ?? ''
}

test('any layer can be hidden, including the last one', () => {
  const store = memory()
  const hidden = toggleLayer(ALL_LAYERS, 'japanese')
  assert.deepEqual(hidden, { japanese: false, hiragana: true, romaji: true, meaning: true })
  writeLayers(store, hidden)
  const none = toggleLayer({ japanese: false, hiragana: false, romaji: false, meaning: true }, 'meaning')
  assert.deepEqual(none, { japanese: false, hiragana: false, romaji: false, meaning: false })
  const shown = toggleLayer(none, 'romaji')
  assert.deepEqual(shown, { japanese: false, hiragana: false, romaji: true, meaning: false })
  assert.equal(store.getItem(LAYER_STORAGE_KEY), JSON.stringify(hidden))
})

test('a throwing store does not block the toggle', () => {
  const store: KeyValueStore = {
    getItem: () => null,
    setItem: () => {
      throw new Error('blocked')
    },
  }
  assert.doesNotThrow(() => writeLayers(store, ALL_LAYERS))
})

test('lyric lines must be ordered, identified, and filled in', () => {
  assert.equal(lyricProblem([]), 'empty')
  assert.equal(lyricProblem([line(1)]), 'index')
  assert.equal(lyricProblem([line(0, 'same'), line(1, 'same')]), 'id')
  const blank = line(0)
  blank.originalText = '   '
  assert.equal(lyricProblem([blank]), 'text')
  const missingHiragana = line(0)
  missingHiragana.readingHiragana = ''
  assert.equal(lyricProblem([missingHiragana]), null)
  assert.equal(lyricProblem([line(0), line(1)]), null)
})

test('routes stay on the library, a new song, and one saved song', () => {
  assert.deepEqual(parseRoute('/'), { name: 'library' })
  assert.deepEqual(parseRoute('/songs/new'), { name: 'new' })
  assert.deepEqual(parseRoute('/import'), { name: 'missing' })
  assert.deepEqual(parseRoute('/songs/akuma-no-ko'), { name: 'song', songId: 'akuma-no-ko' })
  assert.deepEqual(parseRoute('/songs/a%20b'), { name: 'song', songId: 'a b' })
  assert.deepEqual(parseRoute('/missing'), { name: 'missing' })
  assert.equal(songHref('akuma-no-ko'), '/songs/akuma-no-ko')
})

test('language direction names Japanese and English', () => {
  assert.equal(languageDirection('ja', 'en'), 'Japanese → English')
  assert.equal(languageDirection('fr', 'en'), 'fr → English')
})
