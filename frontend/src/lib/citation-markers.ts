const CITATION_MARKER_RE = /\[(\d+)\]/g

/** Rewrites bare "[1]", "[2]" citation markers in agent-generated answer text
 * into markdown links with a `#citation-<messageKey>-N` href, so a
 * ReactMarkdown `a` override can render them as clickable badges that jump
 * to the matching source card instead of navigating anywhere. Anchors are
 * namespaced per message so citation numbers don't collide across the
 * multiple assistant messages rendered on one page. */
export function injectCitationLinks(text: string, messageKey: string | number): string {
  return text.replace(CITATION_MARKER_RE, (match, index) => `[${match}](#${citationAnchorId(messageKey, Number(index) - 1)})`)
}

export function citationAnchorId(messageKey: string | number, index: number): string {
  return `citation-${messageKey}-${index + 1}`
}
