"use client"

import { useQuery } from "@tanstack/react-query"
import { Minus, TrendingDown, TrendingUp } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { getIndexIntraday, getIndexQuotes } from "@/services/market"
import { LivePill } from "./live-pill"

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  const width = 72
  const height = 24
  const step = width / (points.length - 1)
  const path = points
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"} ${(index * step).toFixed(1)} ${(height - ((point - min) / range) * height).toFixed(1)}`
    )
    .join(" ")
  const trendUp = points[points.length - 1] >= points[0]

  return (
    <svg width={width} height={height} className="shrink-0" aria-hidden>
      <path
        d={path}
        fill="none"
        stroke={trendUp ? "var(--positive)" : "var(--negative)"}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

function IndexIcon({ changePercent }: { changePercent: number }) {
  if (changePercent > 0) return <TrendingUp className="size-3.5 text-positive" />
  if (changePercent < 0) return <TrendingDown className="size-3.5 text-negative" />
  return <Minus className="size-3.5 text-muted-foreground" />
}

export function IndexTickerStrip() {
  const quotesQuery = useQuery({
    queryKey: ["market-indices"],
    queryFn: getIndexQuotes,
    refetchInterval: 60_000,
  })
  const intradayQuery = useQuery({
    queryKey: ["market-index-intraday", "NSEI"],
    queryFn: () => getIndexIntraday("NSEI"),
    refetchInterval: 60_000,
  })

  const quotes = quotesQuery.data ?? []
  const sparklinePoints = (intradayQuery.data ?? []).map((point) => point.price)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Markets</h2>
        <LivePill lastUpdated={quotesQuery.dataUpdatedAt ? new Date(quotesQuery.dataUpdatedAt) : undefined} />
      </div>
      {quotesQuery.isLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[74px] w-full" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {quotes.map((quote) => (
            <div key={quote.symbol} className="rounded-xl border border-border bg-card p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">{quote.name}</p>
                  <p className="mt-0.5 truncate text-lg font-semibold">{quote.price.toLocaleString("en-IN")}</p>
                </div>
                {quote.symbol === "^NSEI" && sparklinePoints.length > 1 && <Sparkline points={sparklinePoints} />}
              </div>
              <p
                className={cn(
                  "mt-1 flex items-center gap-1 text-xs font-medium",
                  quote.change_percent > 0
                    ? "text-positive"
                    : quote.change_percent < 0
                      ? "text-negative"
                      : "text-muted-foreground"
                )}
              >
                <IndexIcon changePercent={quote.change_percent} />
                {quote.change > 0 ? "+" : ""}
                {quote.change.toFixed(2)} ({quote.change_percent > 0 ? "+" : ""}
                {quote.change_percent.toFixed(2)}%)
              </p>
            </div>
          ))}
          {quotes.length === 0 && (
            <p className="col-span-full text-sm text-muted-foreground">Market data unavailable right now.</p>
          )}
        </div>
      )}
    </div>
  )
}
