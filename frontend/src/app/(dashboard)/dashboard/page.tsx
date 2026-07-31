"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { Bot, MessageSquare, Minus, Plus, Star, TrendingDown, TrendingUp } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { FollowTickerDialog } from "@/components/stocks/follow-ticker-dialog"
import { IndexTickerStrip } from "@/components/dashboard/index-ticker-strip"
import { MarketMovers } from "@/components/dashboard/market-movers"
import { MarketNewsFeed } from "@/components/dashboard/market-news-feed"
import { formatInr, relativeTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import { listAgentDecisions } from "@/services/agent"
import { getPersona } from "@/services/research"
import { listSessions } from "@/services/research"
import { listFollowedStocks } from "@/services/stocks"
import { useAuthStore } from "@/store/auth-store"
import { useStockDetailStore } from "@/store/stock-detail-store"
import type { AgentDecisionAction } from "@/types/agent"

const ACTION_BADGE: Record<AgentDecisionAction, "positive" | "negative" | "muted"> = {
  buy: "positive",
  avoid: "negative",
  hold: "muted",
}

function SentimentIcon({ label }: { label: string | null }) {
  if (label === "positive") return <TrendingUp className="size-3.5 text-positive" />
  if (label === "negative") return <TrendingDown className="size-3.5 text-negative" />
  return <Minus className="size-3.5 text-muted-foreground" />
}

function StatTile({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-border bg-card p-4"
    >
      <p className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </motion.div>
  )
}

export default function OverviewPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const openStockDetail = useStockDetailStore((state) => state.open)

  const stocksQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })
  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: listSessions })
  const personaQuery = useQuery({ queryKey: ["persona"], queryFn: getPersona })
  const decisionsQuery = useQuery({ queryKey: ["agent-decisions"], queryFn: listAgentDecisions })

  const stocks = stocksQuery.data ?? []
  const sessions = sessionsQuery.data ?? []
  const persona = personaQuery.data

  const scoredSentiments = stocks
    .map((f) => f.stock.rolling_sentiment_score)
    .filter((score): score is number => score != null)
  const avgSentiment =
    scoredSentiments.length > 0 ? scoredSentiments.reduce((a, b) => a + b, 0) / scoredSentiments.length : null

  const firstName = user?.full_name?.split(" ")[0]
  const isLoading = stocksQuery.isLoading || sessionsQuery.isLoading

  return (
    <div className="h-full overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-5xl space-y-8">
        <IndexTickerStrip />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold sm:text-xl">
              {firstName ? `Welcome back, ${firstName}` : "Welcome back"}
            </h1>
            <p className="text-sm text-muted-foreground">Here&apos;s where your research stands today.</p>
          </div>
          <div className="flex gap-2">
            <FollowTickerDialog
              trigger={
                <Button variant="outline" size="sm" className="gap-1.5">
                  <Plus className="size-4" /> Follow ticker
                </Button>
              }
            />
            <Button size="sm" className="gap-1.5" onClick={() => router.push("/chat")}>
              <MessageSquare className="size-4" /> Ask a question
            </Button>
          </div>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Stocks followed" value={stocks.length} />
            <StatTile label="Chat sessions" value={sessions.length} />
            <StatTile
              label="Avg. sentiment"
              value={
                avgSentiment == null ? (
                  "—"
                ) : (
                  <span className="inline-flex items-center gap-1.5">
                    <SentimentIcon label={avgSentiment > 0.1 ? "positive" : avgSentiment < -0.1 ? "negative" : null} />
                    {avgSentiment.toFixed(2)}
                  </span>
                )
              }
              hint="Across followed stocks"
            />
            <StatTile
              label="Investor profile"
              value={persona?.risk_profile ?? "Not set"}
              hint={persona?.investment_style ?? "Tell the agent in chat"}
            />
          </div>
        )}

        {persona?.summary && (
          <div className="rounded-xl border border-border bg-muted/40 p-4">
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Investor memory</p>
            <p className="mt-1 text-sm">{persona.summary}</p>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Followed stocks</h2>
              <Link href="/watchlist" className="text-xs font-medium text-accent-brand hover:underline">
                View all
              </Link>
            </div>
            {stocks.length === 0 && !isLoading && (
              <div className="rounded-xl border border-dashed border-border p-6 text-center">
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
                  className="flex w-full items-center justify-between gap-3 rounded-lg border border-border p-3 text-left transition-colors hover:border-accent-brand/40"
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
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Recent research</h2>
              <Link href="/chat" className="text-xs font-medium text-accent-brand hover:underline">
                Open chat
              </Link>
            </div>
            {sessions.length === 0 && !isLoading && (
              <div className="rounded-xl border border-dashed border-border p-6 text-center">
                <MessageSquare className="mx-auto size-5 text-muted-foreground" />
                <p className="mt-2 text-sm font-medium">No research yet</p>
                <p className="mt-1 text-xs text-muted-foreground">Ask your first question to get started.</p>
              </div>
            )}
            <div className="space-y-2">
              {sessions.slice(0, 5).map((session) => (
                <button
                  key={session.id}
                  onClick={() => router.push(`/chat?session=${session.id}`)}
                  className="block w-full rounded-lg border border-border p-3 text-left transition-colors hover:border-accent-brand/40"
                >
                  <p className="truncate text-sm font-medium">{session.title}</p>
                  <p className="text-xs text-muted-foreground">{relativeTime(session.updated_at)}</p>
                </button>
              ))}
            </div>
          </section>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <MarketMovers />
          <MarketNewsFeed />
        </div>

        {decisionsQuery.data && decisionsQuery.data.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center gap-1.5">
              <Bot className="size-4 text-accent-brand" />
              <h2 className="text-sm font-semibold">Recent agent decisions</h2>
            </div>
            <p className="text-xs text-muted-foreground">
              Paper-only calls the agent made autonomously in your daily briefings — never a real trade.
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {decisionsQuery.data.slice(0, 6).map((decision) => {
                const changePercent =
                  decision.price_at_decision_inr && decision.current_price_inr
                    ? ((decision.current_price_inr - decision.price_at_decision_inr) / decision.price_at_decision_inr) *
                      100
                    : null
                return (
                  <button
                    key={decision.id}
                    onClick={() => openStockDetail(decision.ticker)}
                    className="space-y-1.5 rounded-lg border border-border p-3 text-left transition-colors hover:border-accent-brand/40"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-semibold">{decision.ticker}</span>
                        <Badge variant={ACTION_BADGE[decision.action]}>{decision.action}</Badge>
                      </div>
                      {changePercent != null && (
                        <span
                          className={cn(
                            "text-xs font-medium",
                            changePercent > 0 ? "text-positive" : changePercent < 0 ? "text-negative" : "text-muted-foreground"
                          )}
                        >
                          {changePercent > 0 ? "+" : ""}
                          {changePercent.toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <p className="line-clamp-2 text-xs text-muted-foreground">{decision.reasoning}</p>
                    <p className="text-[11px] text-muted-foreground">
                      {decision.price_at_decision_inr != null && `Called at ${formatInr(decision.price_at_decision_inr)}`}
                      {decision.current_price_inr != null && ` · now ${formatInr(decision.current_price_inr)}`}
                      {" · "}
                      {relativeTime(decision.created_at)}
                    </p>
                  </button>
                )
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
