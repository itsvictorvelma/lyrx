import { useEffect, useRef, useState } from 'react'
import { clampTime, finiteTime, formatTime, playbackRate } from './rehearsal.ts'

const RATES = [0.75, 1, 1.25] as const

export function Player({
  src,
  durationHint,
  following = false,
  seekRequest = null,
  onProgress,
}: {
  src: string
  durationHint?: number | null
  following?: boolean
  seekRequest?: { time: number; token: number } | null
  onProgress?: (current: number, duration: number) => void
}) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const rememberedVolume = useRef(1)
  const onProgressRef = useRef(onProgress)
  const seekToken = useRef(0)
  const [playing, setPlaying] = useState(false)
  const [current, setCurrent] = useState(0)
  const [duration, setDuration] = useState<number | null>(null)
  const [volume, setVolume] = useState(1)
  const [muted, setMuted] = useState(false)
  const [rate, setRate] = useState<(typeof RATES)[number]>(1)
  const [mediaError, setMediaError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    onProgressRef.current = onProgress
  }, [onProgress])

  useEffect(() => {
    const audio = audioRef.current
    return () => audio?.pause()
  }, [])

  useEffect(() => {
    if (!playing) return
    let frame = 0
    const tick = () => {
      const audio = audioRef.current
      const length = audio ? finiteTime(audio.duration) : null
      if (audio && length) onProgressRef.current?.(audio.currentTime, length)
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing])

  useEffect(() => {
    if (!seekRequest || seekRequest.token === seekToken.current) return
    seekToken.current = seekRequest.token
    const audio = audioRef.current
    const length = audio ? (finiteTime(audio.duration) ?? finiteTime(durationHint ?? Number.NaN)) : null
    if (!audio || length == null) return
    audio.currentTime = clampTime(seekRequest.time, length)
    syncClock(audio)
    onProgressRef.current?.(audio.currentTime, length)
  }, [seekRequest, durationHint])

  useEffect(() => {
    if (!following) return
    const audio = audioRef.current
    const length = audio ? finiteTime(audio.duration) : null
    if (!audio || !length || audio.currentTime <= 0) return
    onProgressRef.current?.(audio.currentTime, length)
  }, [following, duration])

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
    onProgressRef.current?.(audio.currentTime, length)
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
  const status = mediaError ?? notice ?? (duration == null ? 'Loading audio.' : '')
  const audible = muted ? 0 : volume

  return (
    <section className="player" aria-label="Audio player">
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
      <div className="player-controls">
        <button type="button" className="button-primary" onClick={() => void togglePlay()}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <button type="button" onClick={() => skip(-10)} disabled={duration == null}>
          Back 10 seconds
        </button>
        <button type="button" onClick={() => skip(10)} disabled={duration == null}>
          Forward 10 seconds
        </button>
        <label className="volume">
          <span>Volume</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={audible}
            aria-valuetext={`${Math.round(audible * 100)} percent`}
            onChange={(event) => changeVolume(Number(event.currentTarget.value))}
          />
        </label>
        <button type="button" aria-pressed={muted} onClick={toggleMute}>
          {muted ? 'Unmute' : 'Mute'}
        </button>
        <div className="rates" role="group" aria-label="Playback rate">
          {RATES.map((item) => (
            <button key={item} type="button" aria-pressed={rate === item} onClick={() => chooseRate(item)}>
              {item}×
            </button>
          ))}
        </div>
        {mediaError ? (
          <button type="button" onClick={reload}>
            Try again
          </button>
        ) : null}
      </div>
      <p className="player-status" role="status">
        {status}
      </p>
    </section>
  )
}
