import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { LyricLine } from './contracts.ts'
import { parseRoute, songHref } from './route.ts'
import {
  ALL_LAYERS,
  LAYER_STORAGE_KEY,
  clampTime,
  formatTime,
  languageDirection,
  lyricProblem,
  playbackRate,
  FOLLOW_STORAGE_KEY,
  followScrollTop,
  readFollow,
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

test('layer storage falls back when missing, invalid, or all hidden', () => {
  assert.deepEqual(readLayers(null), ALL_LAYERS)
  assert.deepEqual(readLayers(memory()), ALL_LAYERS)
  assert.deepEqual(readLayers(memory({ [LAYER_STORAGE_KEY]: '{no' })), ALL_LAYERS)
  assert.deepEqual(readLayers(memory({ [LAYER_STORAGE_KEY]: '{"japanese":false}' })), ALL_LAYERS)
  assert.deepEqual(
    readLayers(memory({ [LAYER_STORAGE_KEY]: '{"japanese":false,"romaji":false,"meaning":false}' })),
    ALL_LAYERS,
  )
  assert.deepEqual(
    readLayers(memory({ [LAYER_STORAGE_KEY]: '{"japanese":false,"romaji":true,"meaning":true}' })),
    { japanese: false, romaji: true, meaning: true },
  )
})

test('the last visible layer cannot be hidden', () => {
  const store = memory()
  const hidden = toggleLayer(ALL_LAYERS, 'japanese')
  assert.deepEqual(hidden, { japanese: false, romaji: true, meaning: true })
  assert.ok(hidden)
  writeLayers(store, hidden)
  const one = toggleLayer({ japanese: false, romaji: false, meaning: true }, 'meaning')
  assert.equal(one, null)
  const shown = toggleLayer({ japanese: false, romaji: false, meaning: true }, 'romaji')
  assert.deepEqual(shown, { japanese: false, romaji: true, meaning: true })
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
  blank.translationEnglish = '   '
  assert.equal(lyricProblem([blank]), 'text')
  assert.equal(lyricProblem([line(0), line(1)]), null)
})

test('follow scroll moves evenly and stays inside the page', () => {
  assert.equal(followScrollTop(0, 100, 500), 100)
  assert.equal(followScrollTop(0.5, 100, 500), 300)
  assert.equal(followScrollTop(1, 100, 500), 500)
  assert.equal(followScrollTop(2, 100, 500), 500)
  assert.equal(followScrollTop(Number.NaN, 100, 500), null)
  assert.equal(followScrollTop(0.2, 400, 100), null)
})

test('follow stays on until the reader turns it off', () => {
  assert.equal(readFollow(null), true)
  assert.equal(readFollow(memory()), true)
  assert.equal(readFollow(memory({ [FOLLOW_STORAGE_KEY]: '0' })), false)
  assert.equal(readFollow(memory({ [FOLLOW_STORAGE_KEY]: '1' })), true)
})

test('routes stay on the library, import, and one song', () => {
  assert.deepEqual(parseRoute('/'), { name: 'library' })
  assert.deepEqual(parseRoute('/import'), { name: 'import' })
  assert.deepEqual(parseRoute('/songs/akuma-no-ko'), { name: 'song', songId: 'akuma-no-ko' })
  assert.deepEqual(parseRoute('/songs/a%20b'), { name: 'song', songId: 'a b' })
  assert.deepEqual(parseRoute('/missing'), { name: 'missing' })
  assert.equal(songHref('akuma-no-ko'), '/songs/akuma-no-ko')
})

test('language direction names Japanese and English', () => {
  assert.equal(languageDirection('ja', 'en'), 'Japanese → English')
  assert.equal(languageDirection('fr', 'en'), 'fr → English')
})
