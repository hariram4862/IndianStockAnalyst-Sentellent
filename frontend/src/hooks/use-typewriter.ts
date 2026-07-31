import { useEffect, useState } from "react"

const CHARS_PER_TICK = 3
const TICK_MS = 12

/** Reveals `text` a few characters at a time. Returns the currently-revealed
 * slice, whether it's finished, and a `skip` function that reveals the rest
 * immediately (e.g. on click). Disabled (`enabled = false`) renders the full
 * text right away -- used for messages loaded from history, not just sent. */
export function useTypewriter(text: string, enabled: boolean) {
  const [trackedText, setTrackedText] = useState(text)
  const [revealedLength, setRevealedLength] = useState(enabled ? 0 : text.length)

  // Reset during render (not in an Effect) when a new message's text arrives --
  // React's documented pattern for adjusting state when a prop changes.
  if (text !== trackedText) {
    setTrackedText(text)
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
