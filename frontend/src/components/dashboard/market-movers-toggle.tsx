"use client"

import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { AnimatePresence, motion } from "framer-motion"

import { Skeleton } from "@/components/ui/skeleton"
import { getMarketMovers } from "@/services/market"
import { listFollowedStocks } from "@/services/stocks"
import { useStockDetailStore } from "@/store/stock-detail-store"
import { LivePill } from "./live-pill"
import type { MarketMover } from "@/types/market"

const TOGGLE_INTERVAL_MS = 3000

function MoverRow({ mover, positive, isFollowed }: { mover: MarketMover; positive: boolean; isFollowed: boolean }) {
  const openStockDetail = useStockDetailStore((state) => state.open)
  const changeLabel = (
    <span className="flex items-center gap-2 text-xs">
      <span className="text-muted-foreground">₹{mover.price.toLocaleString("en-IN")}</span>
      <span className={positive ? "font-medium text-positive" : "font-medium text-negative"}>
        {positive ? "+" : ""}
        {mover.change_percent.toFixed(2)}%
      </span>
    </span>
  )

  if (!isFollowed) {
    return (
      <div className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-sm">
        <span className="font-mono font-medium text-muted-foreground">{mover.ticker}</span>
        {changeLabel}
      </div>
    )
  }

  return (
    <button
      onClick={() => openStockDetail(mover.ticker)}
      className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent"
    >
      <span className="font-mono font-medium">{mover.ticker}</span>
      {changeLabel}
    </button>
  )
}

export function MarketMoversToggle() {
  const [mode, setMode] = useState<"gainers" | "losers">("gainers")

  const moversQuery = useQuery({
    queryKey: ["market-movers"],
    queryFn: getMarketMovers,
    refetchInterval: 5 * 60_000,
  })
  const followedQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })
  const followedTickers = new Set((followedQuery.data ?? []).map((f) => f.stock.ticker))

  useEffect(() => {
    const interval = setInterval(() => {
      setMode((current) => (current === "gainers" ? "losers" : "gainers"))
    }, TOGGLE_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [])

  const movers = (mode === "gainers" ? moversQuery.data?.gainers : moversQuery.data?.losers) ?? []

  return (
    <div className="space-y-3 rounded-xl border border-border p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Market movers</h2>
        <LivePill lastUpdated={moversQuery.dataUpdatedAt ? new Date(moversQuery.dataUpdatedAt) : undefined} />
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setMode("gainers")}
          className={`h-1 w-4 rounded-full transition-colors ${mode === "gainers" ? "bg-positive" : "bg-muted"}`}
          aria-label="Show top gainers"
        />
        <button
          type="button"
          onClick={() => setMode("losers")}
          className={`h-1 w-4 rounded-full transition-colors ${mode === "losers" ? "bg-negative" : "bg-muted"}`}
          aria-label="Show top losers"
        />
        <span className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
          {mode === "gainers" ? "Top gainers" : "Top losers"}
        </span>
      </div>

      {moversQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-7 w-full" />
          ))}
        </div>
      ) : (
        <AnimatePresence mode="wait">
          <motion.div
            key={mode}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25 }}
            className="space-y-1"
          >
            {movers.map((mover) => (
              <MoverRow
                key={mover.ticker}
                mover={mover}
                positive={mode === "gainers"}
                isFollowed={followedTickers.has(mover.ticker)}
              />
            ))}
            {movers.length === 0 && <p className="text-sm text-muted-foreground">No data available.</p>}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  )
}
