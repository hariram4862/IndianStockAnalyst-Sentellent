"use client"

import { useQuery } from "@tanstack/react-query"
import { ExternalLink } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { relativeTime } from "@/lib/format"
import { getMarketNews } from "@/services/market"
import { LivePill } from "./live-pill"

export function MarketNewsFeed() {
  const newsQuery = useQuery({
    queryKey: ["market-news"],
    queryFn: getMarketNews,
    refetchInterval: 3 * 60_000,
  })

  const headlines = newsQuery.data ?? []

  return (
    <div className="space-y-3 rounded-xl border border-border p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Market news</h2>
        <LivePill lastUpdated={newsQuery.dataUpdatedAt ? new Date(newsQuery.dataUpdatedAt) : undefined} />
      </div>
      <div className="max-h-80 space-y-1 overflow-y-auto">
        {newsQuery.isLoading &&
          Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
        {!newsQuery.isLoading && headlines.length === 0 && (
          <p className="text-sm text-muted-foreground">No headlines available right now.</p>
        )}
        {headlines.map((headline) => (
          <a
            key={headline.url}
            href={headline.url}
            target="_blank"
            rel="noreferrer"
            className="group flex items-start justify-between gap-2 rounded-lg px-2 py-2 transition-colors hover:bg-accent"
          >
            <div className="min-w-0">
              <p className="line-clamp-2 text-sm font-medium group-hover:text-accent-brand">{headline.title}</p>
              <div className="mt-1 flex items-center gap-1.5">
                <Badge variant="muted">{headline.source_name.replace(" Markets", "")}</Badge>
                {headline.published_at && (
                  <span className="text-[11px] text-muted-foreground">{relativeTime(headline.published_at)}</span>
                )}
              </div>
            </div>
            <ExternalLink className="mt-1 size-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </a>
        ))}
      </div>
    </div>
  )
}
