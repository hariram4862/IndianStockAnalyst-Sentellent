"use client"

import { useState } from "react"
import { ChevronDown, ExternalLink, Minus, TrendingDown, TrendingUp } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { citationAnchorId } from "@/lib/citation-markers"
import { cn } from "@/lib/utils"
import type { Citation } from "@/types/research"

function SentimentIcon({ label }: { label: string | null }) {
  if (label === "positive") return <TrendingUp className="size-3" />
  if (label === "negative") return <TrendingDown className="size-3" />
  return <Minus className="size-3" />
}

function sentimentBadgeVariant(label: string | null): "positive" | "negative" | "outline" {
  if (label === "positive") return "positive"
  if (label === "negative") return "negative"
  return "outline"
}

function CitationCard({ citation, anchorId }: { citation: Citation; anchorId?: string }) {
  return (
    <div id={anchorId} className="scroll-mt-24 space-y-2 rounded-lg border border-border p-3 transition-colors">
      <div className="flex items-center justify-between gap-2">
        <Badge variant="accent">{citation.ticker}</Badge>
        <span className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          {citation.source_type}
        </span>
      </div>
      <p className="text-sm leading-snug font-medium">{citation.title}</p>
      <p className="line-clamp-3 text-sm text-muted-foreground">{citation.snippet}</p>
      <div className="flex flex-wrap items-center gap-1.5">
        {citation.sentiment_label && (
          <Badge variant={sentimentBadgeVariant(citation.sentiment_label)}>
            <SentimentIcon label={citation.sentiment_label} />
            {citation.sentiment_label}
          </Badge>
        )}
        {citation.impact_label && <Badge variant="outline">{citation.impact_label} impact</Badge>}
        {citation.similarity_score != null && (
          <Badge variant="muted">{Math.round(citation.similarity_score * 100)}% match</Badge>
        )}
      </div>
      {citation.url && (
        <a
          href={citation.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium text-accent-brand hover:underline"
        >
          View source <ExternalLink className="size-3" />
        </a>
      )}
    </div>
  )
}

export function CitationList({ citations, messageKey = "list" }: { citations: Citation[]; messageKey?: string | number }) {
  if (citations.length === 0) {
    return <p className="text-sm text-muted-foreground">No sources for this answer yet.</p>
  }

  return (
    <div className="space-y-3">
      {citations.map((citation, index) => (
        <div
          key={`${citation.ticker}-${index}`}
          className="animate-in fade-in slide-in-from-bottom-1 fill-mode-backwards"
          style={{ animationDelay: `${index * 60}ms`, animationDuration: "300ms" }}
        >
          <CitationCard citation={citation} anchorId={citationAnchorId(messageKey, index)} />
        </div>
      ))}
    </div>
  )
}

/** Collapsible "Sources (N)" block shown directly under a chat message. */
export function MessageSources({
  citations,
  messageKey = "list",
  defaultOpen = true,
}: {
  citations: Citation[]
  messageKey?: string | number
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)

  if (citations.length === 0) return null

  return (
    <div className="mt-2 animate-in fade-in slide-in-from-bottom-1 duration-300">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <ChevronDown className={cn("size-3.5 transition-transform", !open && "-rotate-90")} />
        Sources ({citations.length})
      </button>
      {open && (
        <div className="mt-2">
          <CitationList citations={citations} messageKey={messageKey} />
        </div>
      )}
    </div>
  )
}
