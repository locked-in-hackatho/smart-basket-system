/**
 * Physical feedback for a scan: a short beep and a vibration.
 *
 * A shopper holds the basket at arm's length and is not looking at the
 * screen when they scan, so the sound is the primary confirmation.
 */

let audioContext: AudioContext | null = null

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  try {
    // Browsers block audio until the first user gesture; by the time a scan
    // happens the shopper has already tapped something.
    audioContext ??= new AudioContext()
    if (audioContext.state === 'suspended') void audioContext.resume()
    return audioContext
  } catch {
    return null
  }
}

function tone(frequency: number, durationMs: number, startDelayMs = 0): void {
  const context = getAudioContext()
  if (!context) return

  const start = context.currentTime + startDelayMs / 1000
  const end = start + durationMs / 1000

  const oscillator = context.createOscillator()
  const gain = context.createGain()
  oscillator.type = 'square'
  oscillator.frequency.value = frequency

  // Short fade in/out, otherwise the square wave clicks.
  gain.gain.setValueAtTime(0.0001, start)
  gain.gain.exponentialRampToValueAtTime(0.18, start + 0.008)
  gain.gain.exponentialRampToValueAtTime(0.0001, end)

  oscillator.connect(gain).connect(context.destination)
  oscillator.start(start)
  oscillator.stop(end + 0.02)
}

function vibrate(pattern: number | number[]): void {
  try {
    navigator.vibrate?.(pattern)
  } catch {
    // Vibration is a nice-to-have; desktops and iOS simply do not have it.
  }
}

/** High, bright blip — the product went in. */
export function beepSuccess(): void {
  tone(1320, 90)
  vibrate(35)
}

/** Two low notes — nothing was added, look at the screen. */
export function beepError(): void {
  tone(320, 130)
  tone(240, 160, 140)
  vibrate([60, 50, 60])
}

/** Descending pair — an item came back out of the basket. */
export function beepRemove(): void {
  tone(880, 80)
  tone(620, 90, 85)
  vibrate(25)
}

/** Little fanfare on the thank-you screen. */
export function beepPaid(): void {
  tone(880, 110)
  tone(1175, 110, 110)
  tone(1568, 200, 220)
  vibrate([40, 60, 40, 60, 90])
}
