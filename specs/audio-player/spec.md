---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Audio player specification

Parent plan: [Prototype 1 build plan](../../AGENTS.md)

Host screen and platform:

- [Learn Song](../learn-song/spec.md)
- [Application foundation](../app-foundation/spec.md)

## Goal

Provide a reliable, accessible, responsive player for rehearsal while remaining completely independent from lyric selection, scrolling, and visibility.

## Media contract

- Input is the Song detail `audioUrl`.
- Prototype media is a validated MP3.
- Server/reverse proxy supports HTTPS, correct audio MIME, content length when known, and byte-range requests.
- The player uses `HTMLAudioElement`.
- Playback begins only after a user gesture.
- Media errors never expose storage paths or internal diagnostics.

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
- Browser/default application volume unless a documented local presentation preference is added; do not add server persistence

No restart, next/previous track, loop, A/B loop, line seek, autoplay, auto-scroll, waveform, karaoke, or provider control.

## Behavior

### Play/pause

- One control reflects actual media state, not optimistic state alone.
- Handle rejected play promises with a visible recoverable message.
- Ended state returns the control to “Play”; do not autoplay or loop.

### Seek

- Slider range follows zero to known duration.
- While duration is unknown, disable seeking and communicate loading.
- User seek updates media current time and display.
- Back/forward 10 seconds clamp to `[0, duration]`.
- Seeking does not change playback rate, mute/volume, layer visibility, or manual lyric scroll.

### Elapsed/duration

- Use one consistent `m:ss` or `h:mm:ss` formatter.
- Unknown duration has a non-misleading placeholder.
- Display stays coherent after metadata load, seek, rate change, and media end.
- Updates should feel current without causing excessive full-screen React rerenders.

### Volume and mute

- Volume supports the browser's valid range.
- Mute preserves the previous nonzero volume so unmute restores it.
- A zero volume is communicated consistently with muted state.
- If a platform limits programmatic volume behavior, controls degrade honestly.

### Playback rate

- Only 0.75×, 1×, 1.25×.
- Changing rate preserves position and playing/paused state.
- Current rate is visible and exposed to assistive technology.
- Pitch behavior uses browser support; no custom audio processing is required.

## Sticky responsive layout

- Player remains reachable while lyrics scroll.
- Wider screens: sticky below the application header.
- Narrow screens: safe-area-aware sticky/fixed bottom presentation.
- Reserve enough page space that the final lyric and focused controls are not covered.
- At high zoom or narrow widths, controls may wrap/reflow while retaining order and operability.
- No horizontal overflow.
- Layer toggles and lyric reading order remain independent.

## State model

Track:

- Media readiness/loading/error
- Playing/paused/ended
- Current time
- Duration
- Seeking state
- Volume
- Muted
- Playback rate

Do not track:

- Active lyric line
- Timestamp/cue index
- Loop points
- User/account progress
- Provider/device session

## Error states

- Metadata loading: play may wait; seek disabled; clear status.
- Play blocked/rejected: explain interaction is required and allow retry.
- Unsupported/unreadable source: show Audio unavailable; lyrics remain usable.
- Network interruption: show recoverable failure and retry/reload media.
- Range/seek unsupported: show safe degradation or failure; do not fake success.
- Invalid duration/current time: clamp/fallback and log safe diagnostics.
- Media removed/unpublished: return a safe unavailable state.

Player failure must not crash or remove the lyric content.

## Accessibility

- Every control has a visible or programmatic label.
- Toggle control announces Play/Pause according to state.
- Mute announces mute state.
- Seek and volume expose min/max/current and accessible value text.
- Rate control exposes selected rate.
- Keyboard:
  - Tab reaches every control in logical order.
  - Space/Enter activate buttons.
  - Sliders use standard arrow/page/home/end behavior.
- Touch targets meet mobile sizing guidance.
- Visible focus is never hidden behind sticky content.
- Time updates do not use a noisy assertive live region.
- Errors/status changes are announced politely.
- Do not create undocumented global media keyboard shortcuts in Prototype 1.

## Security and privacy

- No external player SDK, provider API, cookie, account, DRM workaround, or media extraction.
- Only validated same-application/approved media URLs.
- Do not log full URLs containing secrets or local paths.
- No microphone, recording, media-session analytics, or listening history.
- Media must be rights-cleared before public delivery.

## Performance

- Do not rerender every lyric unit on media-time updates.
- Isolate player state from the lyric list.
- Use an update cadence appropriate to elapsed-time display, not karaoke animation.
- Clean up event listeners/object references on song change/unmount.
- Avoid Web Audio; it is unnecessary for the approved controls.

## Tests

### Unit/component

- Time formatting including hour boundary/unknown values
- Play/pause/ended transitions
- Back/forward clamping near zero/end
- Seek behavior with known/unknown duration
- Volume/mute restoration
- Each allowed playback rate and rejection of unsupported values
- Media error rendering and retry
- No callback/state for lyric selection

### Accessibility

- Names, roles, states, and slider values
- Keyboard-only operation
- Focus remains visible in sticky layouts
- Touch target review
- Error/status announcements

### Responsive

- Narrow safe-area bottom player
- Wider sticky-below-header player
- Control wrapping at high zoom
- Final lyric and focused content not obscured
- No horizontal overflow

### Integration/end-to-end

- Real fixture served with byte ranges
- Play/pause and continuous seek
- ±10 seconds at middle and bounds
- Volume/mute
- 0.75×/1×/1.25× without position reset
- Manual lyric scroll and toggles remain unchanged
- Network/media failure leaves lyrics usable
- Assert absence of loop, line seek, autoplay, karaoke, and provider UI

## Sequencing

1. Freeze media delivery and Song detail `audioUrl`.
2. Implement isolated media state hook/controller.
3. Add exact controls and state/error handling.
4. Add responsive sticky layout.
5. Integrate into Learn Song without timeline coupling.
6. Complete accessibility, boundary, real-media, and responsive tests.

May proceed in parallel with Learn Song after the layout envelope and independence contract are agreed.

## Acceptance criteria

- The exact approved controls are present and no others.
- Playback starts only by user action.
- Seek, elapsed/duration, ±10 seconds, volume/mute, and rates behave at boundaries.
- State changes do not reset playback or alter lyrics, toggles, or manual scroll.
- Sticky player remains reachable and never obscures content/focus at supported sizes/zoom.
- Every control is keyboard/touch/screen-reader operable.
- Media failure is understandable and leaves lyrics available.
- No karaoke, timestamp, line seek, loop, autoplay, automation, provider API, or public-upload behavior exists.

## Risks

- Mobile autoplay/volume limitations create misleading controls.
- Sticky UI covers content or the on-screen browser chrome.
- Frequent time updates rerender the lyric list.
- Seek fails when byte-range delivery is misconfigured.
- Scope drifts into line synchronization.

Mitigate with honest capability states, safe-area/layout tests, state isolation, real reverse-proxy media tests, and explicit no-timing contract tests.

## Non-goals and deferred work

- Karaoke/current-line highlighting
- Lyrics-to-audio seeking
- Looping or rehearsal regions
- Autoplay and automated scrolling
- Waveforms
- Media Session/global shortcuts
- Provider SDKs/APIs
- Recording, microphone, pitch analysis
- Saved playback position
