"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Bell, ExternalLink, Minus, MessageSquare, TrendingDown, TrendingUp, X } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { getErrorMessage } from "@/lib/errors"
import { cn } from "@/lib/utils"
import { formatInr, formatInrCrores, formatPercent, relativeTime } from "@/lib/format"
import { RULE_LABELS, ruleSummary } from "@/lib/alert-rules"
import { createAlertRule, deleteAlertRule, listAlertRules } from "@/services/alerts"
import { getStockDetail } from "@/services/stocks"
import { useStockDetailStore } from "@/store/stock-detail-store"
import type { AlertRuleType } from "@/types/agent"

function SentimentIcon({ label }: { label: string | null }) {
  if (label === "positive") return <TrendingUp className="size-3.5 text-positive" />
  if (label === "negative") return <TrendingDown className="size-3.5 text-negative" />
  return <Minus className="size-3.5 text-muted-foreground" />
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">{label}</p>
      <p className="truncate text-sm font-medium">{value}</p>
    </div>
  )
}

function AlertsSection({ ticker }: { ticker: string }) {
  const queryClient = useQueryClient()
  const [ruleType, setRuleType] = useState<AlertRuleType>("negative_sentiment")
  const [threshold, setThreshold] = useState("")

  const rulesQuery = useQuery({ queryKey: ["alert-rules"], queryFn: listAlertRules })
  const rulesForStock = (rulesQuery.data ?? []).filter((rule) => rule.ticker === ticker)

  const createMutation = useMutation({
    mutationFn: () => createAlertRule(ticker, ruleType, ruleType === "debt_threshold" ? Number(threshold) : null),
    onSuccess: () => {
      toast.success("Alert created.")
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] })
      setThreshold("")
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not create alert.")),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAlertRule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] }),
    onError: (error) => toast.error(getErrorMessage(error, "Could not remove alert.")),
  })

  const thresholdMissing = ruleType === "debt_threshold" && !threshold.trim()

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">Alerts</h3>
      <div className="space-y-1.5">
        {rulesForStock.map((rule) => (
          <div
            key={rule.id}
            className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm"
          >
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Bell className="size-3.5" /> {ruleSummary(rule)}
            </span>
            <button
              type="button"
              onClick={() => deleteMutation.mutate(rule.id)}
              className="text-muted-foreground hover:text-destructive"
              aria-label="Remove alert"
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}
        {!rulesQuery.isLoading && rulesForStock.length === 0 && (
          <p className="text-xs text-muted-foreground">No alerts set for this stock.</p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={ruleType}
          onChange={(event) => setRuleType(event.target.value as AlertRuleType)}
          className={cn(
            "h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none",
            "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          )}
        >
          {Object.entries(RULE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        {ruleType === "debt_threshold" && (
          <Input
            type="number"
            step="0.1"
            value={threshold}
            onChange={(event) => setThreshold(event.target.value)}
            placeholder="e.g. 1.5"
            className="w-24"
          />
        )}
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending || thresholdMissing}
        >
          <Bell className="size-3.5" /> Add
        </Button>
      </div>
    </div>
  )
}

export function StockDetailDrawer() {
  const ticker = useStockDetailStore((state) => state.ticker)
  const close = useStockDetailStore((state) => state.close)
  const router = useRouter()

  const detailQuery = useQuery({
    queryKey: ["stock-detail", ticker],
    queryFn: () => getStockDetail(ticker as string),
    enabled: !!ticker,
  })

  const detail = detailQuery.data

  function askAboutStock() {
    if (!ticker) return
    close()
    router.push(`/chat?prompt=${encodeURIComponent(`What's the sentiment on ${ticker} this week?`)}`)
  }

  return (
    <Sheet open={!!ticker} onOpenChange={(next) => !next && close()}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 font-mono">
            {ticker}
            {detail && <Badge variant="outline">{detail.stock.exchange}</Badge>}
          </SheetTitle>
          {detail && <p className="text-sm text-muted-foreground">{detail.stock.company_name}</p>}
        </SheetHeader>

        {detailQuery.isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {detail && (
          <>
            <Button onClick={askAboutStock} className="w-full gap-2">
              <MessageSquare className="size-4" /> Ask about {ticker}
            </Button>

            <div className="grid grid-cols-2 gap-3 rounded-lg border border-border p-4 sm:grid-cols-3">
              <Metric label="Price" value={formatInr(detail.stock.current_price_inr)} />
              <Metric label="Market cap" value={`₹${formatInrCrores(detail.stock.market_cap_inr)}`} />
              <Metric label="P/E" value={detail.stock.pe_ratio?.toFixed(2) ?? "N/A"} />
              <Metric label="Dividend" value={formatPercent(detail.stock.dividend_yield)} />
              <Metric label="Debt/Equity" value={detail.stock.debt_to_equity?.toFixed(2) ?? "N/A"} />
              <Metric
                label="Sentiment"
                value={
                  <span className="inline-flex items-center gap-1">
                    <SentimentIcon label={detail.stock.rolling_sentiment_label} />
                    {detail.stock.rolling_sentiment_label ?? "neutral"}
                  </span>
                }
              />
              {detail.stock.sector && <Metric label="Sector" value={detail.stock.sector} />}
              {detail.stock.industry && <Metric label="Industry" value={detail.stock.industry} />}
              {detail.last_ingested_at && (
                <Metric label="Last refreshed" value={relativeTime(detail.last_ingested_at)} />
              )}
            </div>

            {ticker && <AlertsSection ticker={ticker} />}

            <div className="space-y-2">
              <h3 className="text-sm font-semibold">Grounded sources ({detail.documents.length})</h3>
              <div className="space-y-2">
                {detail.documents.map((doc, index) => (
                  <div key={`${doc.title}-${index}`} className="space-y-1.5 rounded-lg border border-border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
                        {doc.source_type}
                      </span>
                      {doc.sentiment_label && (
                        <Badge
                          variant={
                            doc.sentiment_label === "positive"
                              ? "positive"
                              : doc.sentiment_label === "negative"
                                ? "negative"
                                : "muted"
                          }
                        >
                          <SentimentIcon label={doc.sentiment_label} />
                          {doc.sentiment_label}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm leading-snug font-medium">{doc.title}</p>
                    <p className="line-clamp-2 text-xs text-muted-foreground">{doc.snippet}</p>
                    {doc.url && (
                      <a
                        href={doc.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs font-medium text-accent-brand hover:underline"
                      >
                        View source <ExternalLink className="size-3" />
                      </a>
                    )}
                  </div>
                ))}
                {detail.documents.length === 0 && (
                  <p className="text-sm text-muted-foreground">No ingested sources yet for this stock.</p>
                )}
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
