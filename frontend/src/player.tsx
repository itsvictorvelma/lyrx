import { useEffect, useRef, useState } from 'react'
import { clampTime, finiteTime, formatTime, playbackRate } from './rehearsal.ts'

const RATES = [0.75, 1, 1.25] as const

export function Player({
  src,
  title,
  durationHint,
}: {
  src: string
  title: string
  durationHint?: number | null
}) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const rememberedVolume = useRef(1)
  const [playing, setPlaying] = useState(false)
  const [current, setCurrent] = useState(0)
  const [duration, setDuration] = useState<number | null>(null)
  const [volume, setVolume] = useState(1)
  const [muted, setMuted] = useState(false)
  const [rate, setRate] = useState<(typeof RATES)[number]>(1)
  const [mediaError, setMediaError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    const audio = audioRef.current
    return () => audio?.pause()
  }, [])

  function syncClock(audio: HTMLAudioElement) {
    setCurrent(finiteTime(audio.currentTime) ?? 0)
    setDuration(finiteTime(audio.duration))
  }

  function syncVolume(audio: HTMLAudioElement) {
    if (audio.volume > 0) rememberedVolume.current = audio.volume
    setVolume(audio.volume > 0 ? audio.volume : rememberedVolume.current)
    setMuted(audio.muted || audio.volume === 0)
  }

  async function togglePlay() {
    const audio = audioRef.current
    if (!audio) return
    if (!audio.paused) {
      audio.pause()
      return
    }
    try {
      await audio.play()
      setNotice(null)
    } catch {
      setNotice('Press play to start the audio.')
    }
  }

  function seek(value: number) {
    const audio = audioRef.current
    if (!audio) return
    const length = finiteTime(audio.duration)
    if (length == null) return
    audio.currentTime = clampTime(value, length)
    syncClock(audio)
  }

  function skip(delta: number) {
    const audio = audioRef.current
    if (!audio) return
    seek(audio.currentTime + delta)
  }

  function changeVolume(value: number) {
    const audio = audioRef.current
    if (!audio) return
    const next = Math.min(1, Math.max(0, value))
    if (next > 0) {
      rememberedVolume.current = next
      audio.muted = false
    } else {
      audio.muted = true
    }
    audio.volume = next
    syncVolume(audio)
  }

  function toggleMute() {
    const audio = audioRef.current
    if (!audio) return
    if (audio.muted || audio.volume === 0) {
      const restored = rememberedVolume.current > 0 ? rememberedVolume.current : 1
      audio.muted = false
      audio.volume = restored
    } else {
      rememberedVolume.current = audio.volume
      audio.muted = true
    }
    syncVolume(audio)
  }

  function chooseRate(value: number) {
    const audio = audioRef.current
    const next = playbackRate(value)
    if (!audio || !next) return
    audio.playbackRate = next
    setRate(next)
  }

  function reload() {
    const audio = audioRef.current
    if (!audio) return
    setMediaError(null)
    setNotice(null)
    setDuration(null)
    audio.load()
  }

  const shownDuration = duration ?? finiteTime(durationHint ?? Number.NaN)
  const status = mediaError ?? notice
  const audible = muted ? 0 : volume

  return (
    <section className="player" aria-label={`${title} audio player`}>
      <audio
        ref={audioRef}
        className="player-audio"
        src={src}
        preload="metadata"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={(event) => syncClock(event.currentTarget)}
        onDurationChange={(event) => syncClock(event.currentTarget)}
        onLoadedMetadata={(event) => {
          syncClock(event.currentTarget)
          syncVolume(event.currentTarget)
        }}
        onVolumeChange={(event) => syncVolume(event.currentTarget)}
        onError={() => {
          const code = audioRef.current?.error?.code
          setMediaError(code === 2 ? 'The audio stopped loading. Try again.' : 'Audio unavailable.')
          setDuration(null)
        }}
      />
      <div className="player-main">
        <div className="player-transport">
          <button type="button" className="icon-button is-play" aria-label={playing ? 'Pause' : 'Play'} onClick={() => void togglePlay()}>
            <Icon name={playing ? 'pause' : 'play'} />
          </button>
          <button type="button" className="skip-button" aria-label="Back 10 seconds" disabled={duration == null} onClick={() => skip(-10)}>
            −10
          </button>
          <button type="button" className="skip-button" aria-label="Forward 10 seconds" disabled={duration == null} onClick={() => skip(10)}>
            +10
          </button>
        </div>
        <p className="player-title">{title}</p>
        <div className="player-seek">
          <span className="player-time">{formatTime(current)}</span>
          <input
            type="range"
            min={0}
            max={duration ?? 0}
            step={0.1}
            value={duration == null ? 0 : Math.min(current, duration)}
            disabled={duration == null}
            aria-label="Seek"
            aria-valuetext={formatTime(current)}
            onChange={(event) => seek(Number(event.currentTarget.value))}
          />
          <span className="player-time">{formatTime(shownDuration)}</span>
        </div>
        <div className="player-mix">
          <label className="volume">
            <span className="sr-only">Volume</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={audible}
              aria-label="Volume"
              aria-valuetext={`${Math.round(audible * 100)} percent`}
              onChange={(event) => changeVolume(Number(event.currentTarget.value))}
            />
          </label>
          <button type="button" className="icon-button" aria-pressed={muted} aria-label={muted ? 'Unmute' : 'Mute'} onClick={toggleMute}>
            <Icon name={muted ? 'muted' : 'volume'} />
          </button>
          <div className="rates" role="group" aria-label="Playback rate">
            {RATES.map((item) => (
              <button key={item} type="button" className="rate" aria-pressed={rate === item} onClick={() => chooseRate(item)}>
                {item}×
              </button>
            ))}
          </div>
        </div>
      </div>
      {status ? (
        <div className="player-status" role="status">
          <span>{status}</span>
          {mediaError ? (
            <button type="button" className="text-button" onClick={reload}>
              Try again
            </button>
          ) : null}
        </div>
      ) : (
        <p className="sr-only" role="status">
          {duration == null ? 'Loading audio.' : ''}
        </p>
      )}
    </section>
  )
}

function Icon({ name }: { name: 'play' | 'pause' | 'volume' | 'muted' }) {
  if (name === 'play') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8 5.5v13l11-6.5L8 5.5z" fill="currentColor" />
      </svg>
    )
  }
  if (name === 'pause') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M7 5h3.2v14H7zM13.8 5H17v14h-3.2z" fill="currentColor" />
      </svg>
    )
  }
  if (name === 'muted') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 9.5h3.2L11 6v12l-3.8-3.5H4v-5z" fill="currentColor" />
        <path d="m16 10 4 4m0-4-4 4" fill="none" stroke="currentColor" strokeWidth="1.75" />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 9.5h3.2L11 6v12l-3.8-3.5H4v-5z" fill="currentColor" />
      <path d="M15.5 9.2a3.6 3.6 0 0 1 0 5.6" fill="none" stroke="currentColor" strokeWidth="1.75" />
    </svg>
  )
}
