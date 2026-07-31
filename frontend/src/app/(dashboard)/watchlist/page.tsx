"use client"

import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Minus, RefreshCcw, TrendingDown, TrendingUp } from "lucide-react"
import { z } from "zod"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { getErrorMessage } from "@/lib/errors"
import { formatInr, formatPercent } from "@/lib/format"
import { cn } from "@/lib/utils"
import { followStock, listFollowedStocks, refreshStock } from "@/services/stocks"

const SUGGESTED_TICKERS = [
  "RELIANCE",
  "TCS",
  "HDFCBANK",
  "INFY",
  "ICICIBANK",
  "HINDUNILVR",
  "ITC",
  "SBIN",
  "BHARTIARTL",
  "KOTAKBANK",
  "LT",
  "AXISBANK",
  "ASIANPAINT",
  "MARUTI",
  "SUNPHARMA",
  "TATAMOTORS",
  "WIPRO",
  "ADANIENT",
  "BAJFINANCE",
  "HCLTECH",
]

const followSchema = z.object({
  ticker: z
    .string()
    .trim()
    .min(1, "Enter a ticker")
    .max(15, "Ticker looks too long")
    .regex(/^[A-Za-z]+$/, "Letters only, e.g. RELIANCE"),
})

type FollowFormValues = z.infer<typeof followSchema>

function SentimentIcon({ label }: { label: string | null }) {
  if (label === "positive") return <TrendingUp className="size-3.5" />
  if (label === "negative") return <TrendingDown className="size-3.5" />
  return <Minus className="size-3.5" />
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
  const [refreshingTicker, setRefreshingTicker] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FollowFormValues>({
    resolver: zodResolver(followSchema),
    defaultValues: { ticker: "" },
  })

  const { onChange: onTickerChange, ...tickerField } = register("ticker")

  const stocksQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })

  const followMutation = useMutation({
    mutationFn: (ticker: string) => followStock(ticker),
    onSuccess: (data) => {
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ["followed-stocks"] })
      reset()
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not follow ticker.")),
  })

  const refreshMutation = useMutation({
    mutationFn: (ticker: string) => refreshStock(ticker),
    onMutate: (ticker) => setRefreshingTicker(ticker),
    onSuccess: (data) => {
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ["followed-stocks"] })
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not refresh ticker.")),
    onSettled: () => setRefreshingTicker(null),
  })

  function onSubmit(values: FollowFormValues) {
    followMutation.mutate(values.ticker.trim().toUpperCase())
  }

  const stocks = stocksQuery.data ?? []

  return (
    <div className="h-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-3xl space-y-8">
        <div>
          <h1 className="text-lg font-semibold">Watchlist</h1>
          <p className="text-sm text-muted-foreground">
            Follow an NSE ticker to ingest its fundamentals and recent news for grounded research.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-2">
          <div className="flex gap-2">
            <Input
              placeholder="e.g. RELIANCE"
              aria-invalid={!!errors.ticker}
              {...tickerField}
              onChange={(event) => {
                event.target.value = event.target.value.toUpperCase()
                onTickerChange(event)
              }}
            />
            <Button type="submit" disabled={isSubmitting || followMutation.isPending}>
              {followMutation.isPending ? "Following…" : "Follow"}
            </Button>
          </div>
          {errors.ticker && <p className="text-xs text-destructive">{errors.ticker.message}</p>}

          <div className="flex flex-wrap gap-2 pt-1">
            {SUGGESTED_TICKERS.map((ticker) => (
              <button
                key={ticker}
                type="button"
                onClick={() => setValue("ticker", ticker)}
                className="rounded-full border border-border px-2.5 py-1 font-mono text-[11px] tracking-wide text-muted-foreground transition-colors hover:border-foreground hover:text-foreground"
              >
                {ticker}
              </button>
            ))}
          </div>
        </form>

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

          {stocks.map((followed) => {
            const stock = followed.stock
            const isRefreshing = refreshingTicker === stock.ticker
            return (
              <div key={followed.id} className="space-y-3 rounded-lg border border-border p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold">{stock.ticker}</span>
                      <Badge variant="outline">{stock.exchange}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{stock.company_name}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    onClick={() => refreshMutation.mutate(stock.ticker)}
                    disabled={isRefreshing}
                    aria-label={`Refresh ${stock.ticker}`}
                  >
                    <RefreshCcw className={cn("size-3.5", isRefreshing && "animate-spin")} />
                  </Button>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Metric label="Price" value={formatInr(stock.current_price_inr)} />
                  <Metric label="P/E" value={stock.pe_ratio?.toFixed(2) ?? "N/A"} />
                  <Metric label="Dividend" value={formatPercent(stock.dividend_yield)} />
                  <Metric
                    label="Sentiment"
                    value={
                      <span className="inline-flex items-center gap-1">
                        <SentimentIcon label={stock.rolling_sentiment_label} />
                        {stock.rolling_sentiment_label ?? "neutral"}
                      </span>
                    }
                  />
                </div>

                {stock.fundamentals_summary && (
                  <p className="text-sm text-muted-foreground">{stock.fundamentals_summary}</p>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
