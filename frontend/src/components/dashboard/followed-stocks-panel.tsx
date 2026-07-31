"use client"

import Link from "next/link"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Minus, Star, TrendingDown, TrendingUp } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { SUGGESTED_TICKERS } from "@/config/tickers"
import { getErrorMessage } from "@/lib/errors"
import { followStock, listFollowedStocks } from "@/services/stocks"
import { useStockDetailStore } from "@/store/stock-detail-store"

const MIN_FOLLOWED_BEFORE_SUGGESTIONS = 3
const SUGGESTION_COUNT = 5

function SentimentIcon({ label }: { label: string | null }) {
  if (label === "positive") return <TrendingUp className="size-3.5 text-positive" />
  if (label === "negative") return <TrendingDown className="size-3.5 text-negative" />
  return <Minus className="size-3.5 text-muted-foreground" />
}

export function FollowedStocksPanel() {
  const queryClient = useQueryClient()
  const openStockDetail = useStockDetailStore((state) => state.open)

  const stocksQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })
  const stocks = stocksQuery.data ?? []

  const followMutation = useMutation({
    mutationFn: (ticker: string) => followStock(ticker),
    onSuccess: (data) => {
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ["followed-stocks"] })
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not follow ticker.")),
  })

  const followedTickers = new Set(stocks.map((f) => f.stock.ticker))
  const suggestions = SUGGESTED_TICKERS.filter((ticker) => !followedTickers.has(ticker)).slice(0, SUGGESTION_COUNT)
  const showSuggestions = !stocksQuery.isLoading && stocks.length < MIN_FOLLOWED_BEFORE_SUGGESTIONS

  return (
    <section className="space-y-3 rounded-xl border border-border p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Followed stocks</h2>
        <Link href="/watchlist" className="text-xs font-medium text-accent-brand hover:underline">
          View all
        </Link>
      </div>

      {stocksQuery.isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      )}

      {!stocksQuery.isLoading && stocks.length === 0 && (
        <div className="rounded-xl border border-dashed border-border p-4 text-center">
          <Star className="mx-auto size-5 text-muted-foreground" />
          <p className="mt-2 text-sm font-medium">No stocks yet</p>
          <p className="mt-1 text-xs text-muted-foreground">Follow a ticker to start building your corpus.</p>
        </div>
      )}

      <div className="space-y-2">
        {stocks.slice(0, 5).map((followed) => (
          <button
            key={followed.id}
            onClick={() => openStockDetail(followed.stock.ticker)}
            className="flex w-full items-center justify-between gap-3 rounded-lg border border-border p-2.5 text-left transition-colors hover:border-accent-brand/40"
          >
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold">{followed.stock.ticker}</span>
              <Badge variant="outline">{followed.stock.exchange}</Badge>
            </div>
            <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <SentimentIcon label={followed.stock.rolling_sentiment_label} />
              {followed.stock.rolling_sentiment_label ?? "neutral"}
            </span>
          </button>
        ))}
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <div className="space-y-1.5 border-t border-border pt-3">
          <p className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">Suggestions</p>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((ticker) => (
              <button
                key={ticker}
                type="button"
                onClick={() => followMutation.mutate(ticker)}
                disabled={followMutation.isPending}
                className="rounded-full border border-border px-2.5 py-1 font-mono text-[11px] tracking-wide text-muted-foreground transition-colors hover:border-accent-brand hover:text-accent-brand disabled:opacity-50"
              >
                + {ticker}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
