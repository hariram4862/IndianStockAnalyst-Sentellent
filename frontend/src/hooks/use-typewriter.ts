import { useEffect, useState } from "react"

const CHARS_PER_TICK = 3
const TICK_MS = 12

/** Reveals `text` a few characters at a time. Returns the currently-revealed
 * slice, whether it's finished, and a `skip` function that reveals the rest
 * immediately (e.g. on click). Disabled (`enabled = false`) renders the full
 * text right away -- used for messages loaded from history, not just sent,
 * and also for a message whose animation is interrupted partway through
 * (e.g. `enabled` flips to false mid-reveal) -- it jumps to the full text
 * rather than freezing at whatever partial slice it had reached. */
export function useTypewriter(text: string, enabled: boolean) {
  const [trackedText, setTrackedText] = useState(text)
  const [trackedEnabled, setTrackedEnabled] = useState(enabled)
  const [revealedLength, setRevealedLength] = useState(enabled ? 0 : text.length)

  // Adjust during render (not in an Effect) whenever the text changes or
  // `enabled` transitions -- React's documented pattern for adjusting state
  // from props, and the only way to guarantee a disabled reveal is never
  // left stuck mid-string.
  if (text !== trackedText || enabled !== trackedEnabled) {
    setTrackedText(text)
    setTrackedEnabled(enabled)
    setRevealedLength(enabled ? 0 : text.length)
  }

  useEffect(() => {
    if (!enabled) return
    const interval = setInterval(() => {
      setRevealedLength((current) => {
        const next = current + CHARS_PER_TICK
        if (next >= text.length) {
          clearInterval(interval)
          return text.length
        }
        return next
      })
    }, TICK_MS)
    return () => clearInterval(interval)
  }, [text, enabled])

  return {
    revealed: text.slice(0, revealedLength),
    done: revealedLength >= text.length,
    skip: () => setRevealedLength(text.length),
  }
}
