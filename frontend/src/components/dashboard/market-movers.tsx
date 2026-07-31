"use client"

import { useQuery } from "@tanstack/react-query"

import { Skeleton } from "@/components/ui/skeleton"
import { getMarketMovers } from "@/services/market"
import { listFollowedStocks } from "@/services/stocks"
import { useStockDetailStore } from "@/store/stock-detail-store"
import { LivePill } from "./live-pill"
import type { MarketMover } from "@/types/market"

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

export function MarketMovers() {
  const moversQuery = useQuery({
    queryKey: ["market-movers"],
    queryFn: getMarketMovers,
    refetchInterval: 5 * 60_000,
  })
  const followedQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })
  const followedTickers = new Set((followedQuery.data ?? []).map((f) => f.stock.ticker))

  return (
    <div className="space-y-3 rounded-xl border border-border p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Market movers</h2>
        <LivePill lastUpdated={moversQuery.dataUpdatedAt ? new Date(moversQuery.dataUpdatedAt) : undefined} />
      </div>
      {moversQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-7 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1">
            <p className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">Top gainers</p>
            {(moversQuery.data?.gainers ?? []).map((mover) => (
              <MoverRow key={mover.ticker} mover={mover} positive isFollowed={followedTickers.has(mover.ticker)} />
            ))}
          </div>
          <div className="space-y-1">
            <p className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">Top losers</p>
            {(moversQuery.data?.losers ?? []).map((mover) => (
              <MoverRow key={mover.ticker} mover={mover} positive={false} isFollowed={followedTickers.has(mover.ticker)} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
