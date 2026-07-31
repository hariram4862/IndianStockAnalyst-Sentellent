"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { motion, useAnimationControls } from "framer-motion"
import { ExternalLink } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { relativeTime } from "@/lib/format"
import { getMarketNews } from "@/services/market"
import { LivePill } from "./live-pill"
import type { MarketHeadline } from "@/types/market"

const VIEWPORT_HEIGHT = 320
// Pixels/second the ticker scrolls at -- slow enough to actually read a headline.
const SCROLL_SPEED = 24

function HeadlineRow({ headline }: { headline: MarketHeadline }) {
  return (
    <a
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
  )
}

export function MarketNewsTicker() {
  const newsQuery = useQuery({
    queryKey: ["market-news"],
    queryFn: getMarketNews,
    refetchInterval: 3 * 60_000,
  })

  const headlines = useMemo(() => newsQuery.data ?? [], [newsQuery.data])
  const listRef = useRef<HTMLDivElement>(null)
  const [listHeight, setListHeight] = useState(0)
  const controls = useAnimationControls()
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    if (!listRef.current) return
    setListHeight(listRef.current.scrollHeight)
  }, [headlines])

  useEffect(() => {
    if (paused || listHeight <= VIEWPORT_HEIGHT) {
      controls.stop()
      return
    }
    const duration = listHeight / SCROLL_SPEED
    controls.set({ y: 0 })
    controls.start({
      y: -listHeight,
      transition: { duration, ease: "linear", repeat: Infinity },
    })
  }, [paused, listHeight, controls])

  const scrolls = listHeight > VIEWPORT_HEIGHT

  return (
    <div className="space-y-3 rounded-xl border border-border p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Market news</h2>
        <LivePill lastUpdated={newsQuery.dataUpdatedAt ? new Date(newsQuery.dataUpdatedAt) : undefined} />
      </div>
      <div
        className="overflow-hidden"
        style={{ height: VIEWPORT_HEIGHT }}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        {newsQuery.isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        )}
        {!newsQuery.isLoading && headlines.length === 0 && (
          <p className="text-sm text-muted-foreground">No headlines available right now.</p>
        )}
        {headlines.length > 0 && (
          <motion.div animate={controls}>
            <div ref={listRef} className="space-y-1">
              {headlines.map((headline) => (
                <HeadlineRow key={headline.url} headline={headline} />
              ))}
            </div>
            {scrolls && (
              <div className="space-y-1" aria-hidden>
                {headlines.map((headline) => (
                  <HeadlineRow key={`${headline.url}-repeat`} headline={headline} />
                ))}
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  )
}
