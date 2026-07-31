"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { toast } from "sonner"
import { MessageSquare, Minus, Plus, RefreshCcw, TrendingDown, TrendingUp, X } from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { FollowTickerDialog } from "@/components/stocks/follow-ticker-dialog"
import { getErrorMessage } from "@/lib/errors"
import { formatInr, formatPercent, relativeTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import { listFollowedStocks, refreshStock, unfollowStock } from "@/services/stocks"
import { useStockDetailStore } from "@/store/stock-detail-store"

function SentimentIcon({ label }: { label: string | null }) {
  if (label === "positive") return <TrendingUp className="size-3.5" />
  if (label === "negative") return <TrendingDown className="size-3.5" />
  return <Minus className="size-3.5" />
}

function sentimentTextClass(label: string | null) {
  if (label === "positive") return "text-positive"
  if (label === "negative") return "text-negative"
  return "text-muted-foreground"
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  )
}

export default function WatchlistPage() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const openStockDetail = useStockDetailStore((state) => state.open)
  const [refreshingTicker, setRefreshingTicker] = useState<string | null>(null)
  const [unfollowingTicker, setUnfollowingTicker] = useState<string | null>(null)

  const stocksQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })

  const refreshMutation = useMutation({
    mutationFn: (ticker: string) => refreshStock(ticker),
    onMutate: (ticker) => setRefreshingTicker(ticker),
    onSuccess: (data) => {
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ["followed-stocks"] })
      queryClient.invalidateQueries({ queryKey: ["stock-detail"] })
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not refresh ticker.")),
    onSettled: () => setRefreshingTicker(null),
  })

  const unfollowMutation = useMutation({
    mutationFn: (ticker: string) => unfollowStock(ticker),
    onSuccess: (data) => {
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ["followed-stocks"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] })
      setUnfollowingTicker(null)
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not unfollow ticker.")),
  })

  function askAboutStock(ticker: string) {
    router.push(`/chat?prompt=${encodeURIComponent(`What's the sentiment on ${ticker} this week?`)}`)
  }

  const stocks = stocksQuery.data ?? []

  return (
    <div className="h-full overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-3xl space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold">Watchlist</h1>
            <p className="text-sm text-muted-foreground">
              Follow an NSE ticker to ingest its fundamentals and recent news for grounded research.
            </p>
          </div>
          <FollowTickerDialog
            trigger={
              <Button size="sm" className="gap-1.5">
                <Plus className="size-4" /> Follow ticker
              </Button>
            }
          />
        </div>

        <div className="space-y-3">
          {stocksQuery.isLoading &&
            Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-24 w-full" />)}

          {!stocksQuery.isLoading && stocks.length === 0 && (
            <div className="rounded-lg border border-dashed border-border p-8 text-center">
              <p className="text-sm font-medium">No stocks followed yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Follow your first ticker above to start building your research corpus.
              </p>
            </div>
          )}

          {stocks.map((followed, index) => {
            const stock = followed.stock
            const isRefreshing = refreshingTicker === stock.ticker
            return (
              <motion.div
                key={followed.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: Math.min(index, 6) * 0.05 }}
                className="space-y-3 rounded-lg border border-border p-4 transition-colors hover:border-accent-brand/30"
              >
                <div className="flex items-start justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => openStockDetail(stock.ticker)}
                    className="min-w-0 text-left"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold hover:underline">{stock.ticker}</span>
                      <Badge variant="outline">{stock.exchange}</Badge>
                    </div>
                    <p className="truncate text-sm text-muted-foreground">{stock.company_name}</p>
                  </button>
                  <div className="flex shrink-0 items-center gap-1">
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => askAboutStock(stock.ticker)}
                      aria-label={`Ask about ${stock.ticker}`}
                    >
                      <MessageSquare className="size-3.5" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => refreshMutation.mutate(stock.ticker)}
                      disabled={isRefreshing}
                      aria-label={`Refresh ${stock.ticker}`}
                    >
                      <RefreshCcw className={cn("size-3.5", isRefreshing && "animate-spin")} />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon-sm"
                      onClick={() => setUnfollowingTicker(stock.ticker)}
                      aria-label={`Unfollow ${stock.ticker}`}
                    >
                      <X className="size-3.5" />
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Metric label="Price" value={formatInr(stock.current_price_inr)} />
                  <Metric label="P/E" value={stock.pe_ratio?.toFixed(2) ?? "N/A"} />
                  <Metric label="Dividend" value={formatPercent(stock.dividend_yield)} />
                  <Metric
                    label="Sentiment"
                    value={
                      <span className={cn("inline-flex items-center gap-1", sentimentTextClass(stock.rolling_sentiment_label))}>
                        <SentimentIcon label={stock.rolling_sentiment_label} />
                        {stock.rolling_sentiment_label ?? "neutral"}
                      </span>
                    }
                  />
                </div>

                {stock.fundamentals_summary && (
                  <p className="text-sm text-muted-foreground">{stock.fundamentals_summary}</p>
                )}

                {followed.last_ingested_at && (
                  <p className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
                    Last refreshed {relativeTime(followed.last_ingested_at)}
                  </p>
                )}
              </motion.div>
            )
          })}
        </div>
      </div>

      <AlertDialog open={unfollowingTicker != null} onOpenChange={(open) => !open && setUnfollowingTicker(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Unfollow {unfollowingTicker}?</AlertDialogTitle>
            <AlertDialogDescription>
              We&apos;ll stop refreshing its news and fundamentals. Following it again later won&apos;t re-ingest
              duplicate data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setUnfollowingTicker(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => unfollowingTicker && unfollowMutation.mutate(unfollowingTicker)}
              disabled={unfollowMutation.isPending}
            >
              Unfollow
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
