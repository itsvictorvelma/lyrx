# Audio player specification

Prototype 2.

Host screen and platform:

- [Learn Song](../learn-song/spec.md)
- [Application foundation](../app-foundation/spec.md)

## Goal

Play one MP3 the learner attaches, on the lyric screen, without tying playback time to the lyrics.

The song stays readable with no audio. Spotify playback is out of scope. Lyric following from the clock is out of scope.

## Media contract

- Input is the Song detail `audioUrl`.
- `audioUrl` may be null. The player then shows that no audio is attached and does not load a source. Seek, skip, and play stay disabled. Lyrics stay on the page. The attach control is specified in [Song creation](../song-creation/spec.md).
- The file is a validated MP3.
- Server or reverse proxy supports HTTPS, correct audio MIME, content length when known, and byte-range requests.
- The player uses `HTMLAudioElement`.
- Playback begins only after a user gesture.
- Media errors never expose storage paths or internal diagnostics.
- The player does not load a provider SDK, a stream, or a remote catalog.

## Approved controls

The player contains exactly:

- Play/pause
- Continuous seek control
- Elapsed time and total duration
- Back 10 seconds
- Forward 10 seconds
- Volume control
- Mute/unmute
- Playback rates:
  - 0.75×
  - 1×
  - 1.25×

Defaults:

- Paused
- Position zero
- Playback rate 1×
- Browser or default application volume. Do not add server persistence for volume.

No restart, next or previous track, loop, A/B loop, line seek, autoplay, auto-scroll, waveform, karaoke, or provider control.

## Behavior

### Play/pause

- One control reflects actual media state, not optimistic state alone.
- Handle rejected play promises with a visible recoverable message.
- Ended state returns the control to Play. Do not autoplay or loop.

### Seek

- Slider range follows zero to known duration.
- While duration is unknown, disable seeking and communicate loading.
- User seek updates media current time and display.
- Back and forward 10 seconds clamp to `[0, duration]`.
- Seeking does not change playback rate, mute, volume, layer visibility, manual lyric scroll, or the lyric line mark.

### Elapsed and duration

- Use one consistent `m:ss` or `h:mm:ss` formatter.
- Unknown duration has a non-misleading placeholder.
- Display stays coherent after metadata load, seek, rate change, and media end.
- Updates should feel current without causing a full-screen React rerender.
- Publishing the current time does not highlight a lyric line and does not scroll the lyrics.

### Volume and mute

- Volume supports the browser's valid range.
- Mute preserves the previous nonzero volume so unmute restores it.
- A zero volume is communicated consistently with muted state.
- If a platform limits programmatic volume, the controls show that limit.

### Playback rate

- Only 0.75×, 1×, and 1.25×.
- Changing rate preserves position and playing or paused state.
- Current rate is visible and exposed to assistive technology.
- Pitch behavior uses browser support. No custom audio processing is required.

## Layout

- The player is a compact bar on the lyric screen: play/pause, back and forward 10 seconds, the song title, seek, elapsed time and duration, volume, mute, and playback rate.
- Play, pause, and mute are icons. Their accessible names stay Play, Pause, Mute, and Unmute. The 10-second controls read −10 and +10, with the accessible names Back 10 seconds and Forward 10 seconds.
- The bar sits with the song, in normal flow, under the header and above the documents. The page scrolls. The bar is not a fixed bottom sheet and does not cover the last lyric or a focused control.
- The bar is not a sidebar, and it does not sit beside a song list.
- At high zoom or narrow widths, controls may wrap while retaining order and operability.
- No horizontal overflow.
- Layer visibility and lyric reading order stay independent of the bar.

## State model

Track:

- Media readiness, loading, and error
- Playing, paused, and ended
- Current time
- Duration
- Seeking state
- Volume
- Muted
- Playback rate

Do not track:

- Active lyric line
- Timestamp or cue index
- Loop points
- User or account progress
- Provider or device session

## Error states

- No MP3 attached: status says audio is not attached. Transport controls that need a file stay disabled.
- Metadata loading: play may wait; seek disabled; clear status.
- Play blocked or rejected: explain that interaction is required and allow retry.
- Unsupported or unreadable source: show Audio unavailable. Lyrics remain usable.
- Network interruption: show a recoverable failure and retry or reload the media.
- Range or seek unsupported: show a safe failure. Do not report success.
- Invalid duration or current time: clamp or fall back, and log a safe diagnostic.
- Media removed: return a safe unavailable state.

Player failure must not crash the page or remove the lyrics.

## Accessibility

- Every control has a visible or programmatic label.
- The play control announces Play or Pause according to state.
- Mute announces mute state.
- Seek and volume expose min, max, current value, and accessible value text.
- Rate control exposes the selected rate.
- Keyboard:
  - Tab reaches every control in logical order.
  - Space and Enter activate buttons.
  - Sliders use standard arrow, page, home, and end behavior.
- Touch targets meet mobile sizing guidance.
- Visible focus is never hidden by the bar.
- Time updates do not use a noisy assertive live region.
- Errors and status changes are announced politely.
- Do not add global media keyboard shortcuts.

## Security and privacy

- No external player SDK, provider API, cookie, account, DRM workaround, or media extraction.
- No Spotify playback and no Spotify SDK.
- Only validated same-application media URLs.
- Do not log full URLs containing secrets or local paths.
- No microphone, recording, media-session analytics, or listening history.

## Performance

- Do not rerender the lyric documents on each media-time update.
- Isolate player state from the lyric list.
- Use an update cadence appropriate to the elapsed-time display.
- Clean up event listeners and object references on song change and unmount.
- Avoid Web Audio. The approved controls do not need it.

## Tests

### Unit and component

- Time formatting, including the hour boundary and unknown values
- Play, pause, and ended transitions
- Back and forward clamping near zero and near the end
- Seek behavior with known and unknown duration
- Volume and mute restoration
- Each allowed playback rate, and rejection of other rates
- Media error rendering and retry
- No lyric-line state and no scroll call from time updates

### Accessibility

- Names, roles, states, and slider values
- Keyboard-only operation
- Focus remains visible
- Touch target review
- Error and status announcements

### Responsive

- Narrow and wide: compact bar with the song, lyrics filling the screen
- Control wrapping at high zoom
- Final lyric and focused content not obscured
- No horizontal overflow
- No song column introduced by the player

### Integration and end-to-end

- Real fixture served with byte ranges
- Play, pause, and continuous seek
- ±10 seconds at the middle and at the bounds
- Volume and mute
- 0.75×, 1×, and 1.25× without a position reset
- Manual lyric scroll and document toggles stay unchanged
- Network or media failure leaves the lyrics usable
- Assert absence of loop, line seek, autoplay, karaoke, Spotify, and lyric following from the clock

## Acceptance criteria

- The approved controls are present, and no others.
- Playback starts only by user action.
- Seek, elapsed time, duration, ±10 seconds, volume, mute, and rates behave at the boundaries.
- State changes do not reset playback or alter the lyrics, the toggles, the line mark, or manual scroll.
- Playback time does not highlight a line and does not scroll the lyrics.
- The bar stays reachable and does not cover content or focus at supported sizes and zoom.
- Every control is operable by keyboard, touch, and screen reader.
- Media failure is understandable and leaves the lyrics available.
- One optional MP3 is the only audio. No line timing, loop, autoplay, Spotify playback, or provider API.

## Risks

- Mobile autoplay and volume limits can make a control look more capable than it is.
- The bar can cover content or the browser chrome.
- Frequent time updates can rerender the lyric documents or drive a line mark.
- Seek fails when byte-range delivery is misconfigured.
- A provider embed can replace the MP3.

## Out of scope

- Spotify playback
- Lyric following from the clock
- Karaoke and current-line highlighting from playback time
- Lyrics-to-audio seeking
- Looping and rehearsal regions
- Autoplay and automated scrolling
- Waveforms
- Media Session and global shortcuts
- Provider SDKs and provider APIs
- Recording, microphone, and pitch analysis
- Saved playback position
