"use client"

import { useState } from "react"
import ReactMarkdown from "react-markdown"
import { Check, Copy } from "lucide-react"

import { citationAnchorId, injectCitationLinks } from "@/lib/citation-markers"
import { useTypewriter } from "@/hooks/use-typewriter"
import { cn } from "@/lib/utils"

function CitationMarkerLink({ href, children }: { href?: string; children?: React.ReactNode }) {
  if (href?.startsWith("#citation-")) {
    return (
      <a
        href={href}
        onClick={(event) => {
          event.preventDefault()
          const el = document.getElementById(href.slice(1))
          el?.scrollIntoView({ behavior: "smooth", block: "center" })
          el?.classList.add("ring-2", "ring-accent-brand")
          setTimeout(() => el?.classList.remove("ring-2", "ring-accent-brand"), 1200)
        }}
        className="mx-0.5 inline-flex size-4 items-center justify-center rounded-full bg-accent-brand/15 align-text-top font-mono text-[10px] font-semibold text-accent-brand no-underline hover:bg-accent-brand/25"
      >
        {children}
      </a>
    )
  }
  return (
    <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2">
      {children}
    </a>
  )
}

interface AssistantMessageProps {
  content: string
  messageKey: string | number
  animate: boolean
  className?: string
}

export function AssistantMessage({ content, messageKey, animate, className }: AssistantMessageProps) {
  const { revealed, done, skip } = useTypewriter(content, animate)
  const [copied, setCopied] = useState(false)

  async function copy() {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div
      className={cn("group relative", className)}
      onClick={() => {
        if (!done) skip()
      }}
    >
      <div className="max-w-none text-sm leading-relaxed break-words [&_h1]:mt-2 [&_h1]:mb-1.5 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mt-2 [&_h2]:mb-1.5 [&_h2]:text-sm [&_h2]:font-semibold [&_li]:my-0.5 [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1.5 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_strong]:text-foreground [&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5">
        <ReactMarkdown components={{ a: CitationMarkerLink }}>
          {injectCitationLinks(revealed, messageKey)}
        </ReactMarkdown>
        {!done && <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-foreground/60 align-middle" />}
      </div>
      {done && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation()
            copy()
          }}
          className="mt-1 inline-flex items-center gap-1 text-[11px] text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100"
        >
          {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      )}
    </div>
  )
}

export { citationAnchorId }
