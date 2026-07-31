"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowUpRight, LoaderCircle, LogOut, RefreshCcw } from "lucide-react"

import AuthGuard from "@/components/auth/AuthGuard"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { sendResearchMessage } from "@/services/research"
import { followStock, listFollowedStocks, refreshStock } from "@/services/stocks"
import { useAuthStore } from "@/store/auth-store"
import type { Citation, ChatResponse } from "@/types/research"
import type { FollowedStock } from "@/types/stock"

type ChatTurn = {
  role: "user" | "assistant"
  content: string
  citations?: Citation[]
}

// Suggestions only -- the ticker input accepts any NSE symbol (validated
// server-side against yfinance), this list just speeds up common picks.
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

function formatInr(value: number | null) {
  if (value == null) return "N/A"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value)
}

function formatPercent(value: number | null) {
  if (value == null) return "N/A"
  return `${value.toFixed(2)}%`
}

function initialsFromName(name?: string) {
  if (!name) return "IA"
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("")
}

function sentimentTone(label: string | null) {
  if (label === "positive") return "text-emerald-700"
  if (label === "negative") return "text-rose-700"
  return "text-stone-600"
}

export default function DashboardPage() {
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const [followedStocks, setFollowedStocks] = useState<FollowedStock[]>([])
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [ticker, setTicker] = useState("RELIANCE")
  const [tickerStatus, setTickerStatus] = useState<string | null>(null)
  const [tickerError, setTickerError] = useState<string | null>(null)
  const [isFollowing, setIsFollowing] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isLoadingStocks, setIsLoadingStocks] = useState(true)

  const [message, setMessage] = useState("")
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([])
  const [personaSummary, setPersonaSummary] = useState<string | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)

  const activeFollowedStock = useMemo(() => {
    if (selectedTicker) {
      const selected = followedStocks.find((item) => item.stock.ticker === selectedTicker)
      if (selected) return selected
    }
    return followedStocks[0] ?? null
  }, [followedStocks, selectedTicker])

  useEffect(() => {
    void loadFollowedStocks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadFollowedStocks() {
    setIsLoadingStocks(true)
    setTickerError(null)

    try {
      const stocks = await listFollowedStocks()
      setFollowedStocks(stocks)
      if (stocks.length > 0 && !selectedTicker) {
        setSelectedTicker(stocks[0].stock.ticker)
      }
    } catch (error) {
      setTickerError(getErrorMessage(error, "Could not load followed stocks."))
    } finally {
      setIsLoadingStocks(false)
    }
  }

  async function handleFollowStock() {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) return

    setIsFollowing(true)
    setTickerError(null)
    setTickerStatus(null)

    try {
      const result = await followStock(normalizedTicker)
      setTickerStatus(result.message)
      setSelectedTicker(result.followed_stock.stock.ticker)
      setTicker(normalizedTicker)
      await loadFollowedStocks()
    } catch (error) {
      setTickerError(getErrorMessage(error, "Could not follow ticker."))
    } finally {
      setIsFollowing(false)
    }
  }

  async function handleRefreshStock() {
    if (!activeFollowedStock) return

    setIsRefreshing(true)
    setTickerError(null)
    setTickerStatus(null)

    try {
      const result = await refreshStock(activeFollowedStock.stock.ticker)
      setTickerStatus(result.message)
      await loadFollowedStocks()
    } catch (error) {
      setTickerError(getErrorMessage(error, "Could not refresh ticker."))
    } finally {
      setIsRefreshing(false)
    }
  }

  async function handleSendMessage() {
    const trimmed = message.trim()
    if (!trimmed) return

    setIsSending(true)
    setChatError(null)
    setChatTurns((current) => [...current, { role: "user", content: trimmed }])
    setMessage("")

    try {
      const result: ChatResponse = await sendResearchMessage(trimmed, sessionId)
      setSessionId(result.session_id)
      setPersonaSummary(result.persona_summary)
      setChatTurns((current) => [
        ...current,
        {
          role: "assistant",
          content: result.answer,
          citations: result.citations,
        },
      ])
    } catch (error) {
      setChatTurns((current) => current.slice(0, -1))
      setChatError(getErrorMessage(error, "Could not send message."))
      setMessage(trimmed)
    } finally {
      setIsSending(false)
    }
  }

  function handleLogout() {
    logout()
    router.replace("/login")
  }

  const activeStock = activeFollowedStock?.stock ?? null

  return (
    <AuthGuard>
      <main className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
        <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1600px] overflow-hidden rounded-[2rem] border border-stone-300/70 bg-[linear-gradient(180deg,rgba(252,250,244,0.96),rgba(246,243,234,0.96))] shadow-[0_40px_120px_rgba(44,49,36,0.12)] lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="border-b border-stone-300/80 p-6 lg:border-r lg:border-b-0 lg:p-8">
            <div className="flex h-full flex-col">
              <div className="space-y-6">
                <div className="space-y-3">
                  <p className="font-mono text-[11px] uppercase tracking-[0.35em] text-stone-500">
                    Sentellent / Phase 2
                  </p>
                  <div className="space-y-2">
                    <h1 className="max-w-[12ch] font-heading text-5xl leading-[0.92] tracking-tight text-stone-900 sm:text-6xl">
                      Indian equity research, quietly done.
                    </h1>
                    <p className="max-w-xs text-sm leading-6 text-stone-600">
                      A minimal research room for grounded Indian-stock analysis, dynamic memory,
                      and cited answers in INR.
                    </p>
                  </div>
                </div>

                <div className="rounded-[1.6rem] border border-stone-300 bg-stone-50/80 p-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-stone-500">
                    Analyst
                  </p>
                  <div className="mt-3 flex items-center gap-3">
                    <div className="flex size-11 items-center justify-center rounded-full border border-stone-300 bg-white text-sm font-semibold text-stone-800">
                      {initialsFromName(user?.full_name)}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-base font-medium text-stone-900">{user?.full_name}</p>
                      <p className="truncate text-xs text-stone-500">{user?.email}</p>
                    </div>
                  </div>
                  <Button className="mt-4 w-full" variant="outline" onClick={handleLogout}>
                    <LogOut className="size-4" />
                    Sign out
                  </Button>
                </div>

                <div className="space-y-3">
                  <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-stone-500">
                    Add coverage
                  </p>
                  <div className="flex gap-2">
                    <Input
                      className="border-stone-300 bg-stone-50"
                      value={ticker}
                      onChange={(event) => setTicker(event.target.value.toUpperCase())}
                      placeholder="Ticker"
                    />
                    <Button onClick={handleFollowStock} disabled={isFollowing}>
                      {isFollowing ? "..." : "Add"}
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTED_TICKERS.map((suggestion) => (
                      <button
                        key={suggestion}
                        className="rounded-full border border-stone-300 px-3 py-1.5 font-mono text-[11px] tracking-[0.2em] text-stone-600 transition hover:border-stone-800 hover:text-stone-900"
                        onClick={() => setTicker(suggestion)}
                        type="button"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-8 space-y-3 lg:mt-auto">
                <div className="flex items-center justify-between">
                  <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-stone-500">
                    Covered names
                  </p>
                  {activeStock ? (
                    <button
                      className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.2em] text-stone-600 transition hover:text-stone-900"
                      onClick={handleRefreshStock}
                      type="button"
                    >
                      {isRefreshing ? <LoaderCircle className="size-3 animate-spin" /> : <RefreshCcw className="size-3" />}
                      Refresh
                    </button>
                  ) : null}
                </div>

                <div className="space-y-2">
                  {followedStocks.map((followed) => {
                    const isActive = followed.stock.ticker === activeStock?.ticker
                    return (
                      <button
                        key={followed.id}
                        className={`w-full rounded-[1.4rem] border px-4 py-3 text-left transition ${
                          isActive
                            ? "border-stone-900 bg-stone-900 text-stone-50"
                            : "border-stone-300 bg-stone-50/60 text-stone-800 hover:border-stone-500"
                        }`}
                        onClick={() => setSelectedTicker(followed.stock.ticker)}
                        type="button"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="font-mono text-[11px] uppercase tracking-[0.22em] opacity-70">
                              {followed.stock.exchange}
                            </p>
                            <p className="mt-1 text-lg font-medium">{followed.stock.ticker}</p>
                          </div>
                          <ArrowUpRight className="size-4 opacity-70" />
                        </div>
                        <p className="mt-2 line-clamp-2 text-sm opacity-80">{followed.stock.company_name}</p>
                      </button>
                    )
                  })}

                  {!isLoadingStocks && followedStocks.length === 0 ? (
                    <div className="rounded-[1.4rem] border border-dashed border-stone-300 px-4 py-5 text-sm text-stone-500">
                      Add a ticker to begin research coverage.
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </aside>

          <section className="grid gap-0 lg:grid-cols-[minmax(0,0.95fr)_minmax(320px,0.75fr)]">
            <div className="border-b border-stone-300/80 p-6 lg:border-r lg:border-b-0 lg:p-10">
              <div className="space-y-8">
                <header className="space-y-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.35em] text-stone-500">
                    Research canvas
                  </p>
                  <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_220px]">
                    <div className="space-y-3">
                      <h2 className="font-heading text-4xl leading-none tracking-tight text-stone-950 sm:text-5xl">
                        {activeStock ? activeStock.company_name : "Build your coverage list"}
                      </h2>
                      <p className="max-w-2xl text-base leading-7 text-stone-600">
                        {activeStock
                          ? activeStock.fundamentals_summary
                          : "Follow one Indian stock first. The agent will ingest fundamentals and market coverage, then answer only from the retrieved corpus."}
                      </p>
                    </div>

                    <div className="space-y-2 border-t border-stone-300 pt-3 lg:border-t-0 lg:border-l lg:pl-6">
                      <Metric label="Price" value={formatInr(activeStock?.current_price_inr ?? null)} />
                      <Metric label="P/E" value={activeStock?.pe_ratio?.toFixed(2) ?? "N/A"} />
                      <Metric label="Dividend" value={formatPercent(activeStock?.dividend_yield ?? null)} />
                      <Metric
                        label="Sentiment"
                        value={
                          activeStock?.rolling_sentiment_label
                            ? `${activeStock.rolling_sentiment_label} ${
                                activeStock.rolling_sentiment_score != null
                                  ? `(${activeStock.rolling_sentiment_score.toFixed(2)})`
                                  : ""
                              }`
                            : "N/A"
                        }
                        valueClassName={sentimentTone(activeStock?.rolling_sentiment_label ?? null)}
                      />
                    </div>
                  </div>
                </header>

                {personaSummary ? (
                  <div className="rounded-[1.6rem] border border-emerald-700/25 bg-emerald-50/70 px-5 py-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-emerald-700">
                      Investor memory
                    </p>
                    <p className="mt-2 text-sm leading-6 text-stone-700">{personaSummary}</p>
                  </div>
                ) : null}

                <div className="space-y-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-stone-500">
                    Ask the analyst
                  </p>
                  <textarea
                    className="min-h-40 w-full rounded-[1.8rem] border border-stone-300 bg-stone-50/70 px-5 py-4 text-[15px] leading-7 text-stone-900 outline-none transition focus:border-stone-900 focus:ring-4 focus:ring-stone-900/5"
                    onChange={(event) => setMessage(event.target.value)}
                    placeholder="What is the sentiment on TCS this week? Or describe your investor style."
                    value={message}
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button onClick={handleSendMessage} disabled={isSending || followedStocks.length === 0}>
                      {isSending ? "Thinking..." : "Run grounded query"}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() =>
                        setMessage("I'm a conservative, dividend-focused investor and I avoid high-debt companies.")
                      }
                    >
                      Persona memory
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setMessage("What is the sentiment on RELIANCE this week?")}
                    >
                      Sentiment check
                    </Button>
                  </div>
                  {tickerStatus ? <Notice tone="success" message={tickerStatus} /> : null}
                  {tickerError ? <Notice tone="error" message={tickerError} /> : null}
                  {chatError ? <Notice tone="error" message={chatError} /> : null}
                </div>
              </div>
            </div>

            <div className="p-6 lg:p-10">
              <div className="space-y-6">
                <div className="flex items-end justify-between gap-4 border-b border-stone-300 pb-4">
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-stone-500">
                      Conversation
                    </p>
                    <h3 className="mt-2 font-heading text-3xl leading-none text-stone-950">
                      Retrieved evidence
                    </h3>
                  </div>
                  <p className="max-w-[18ch] text-right text-xs leading-5 text-stone-500">
                    Every claim should be grounded, cited, and priced in INR.
                  </p>
                </div>

                <div className="space-y-4">
                  {chatTurns.length === 0 ? (
                    <div className="rounded-[1.6rem] border border-dashed border-stone-300 bg-stone-50/50 px-5 py-6 text-sm leading-7 text-stone-500">
                      No response yet. Follow a stock, refresh if needed, then ask a grounded research question.
                    </div>
                  ) : null}

                  {chatTurns.map((turn, index) => (
                    <article
                      key={`${turn.role}-${index}`}
                      className={`rounded-[1.8rem] border px-5 py-5 ${
                        turn.role === "user"
                          ? "border-stone-900 bg-stone-900 text-stone-50"
                          : "border-stone-300 bg-stone-50/70 text-stone-800"
                      }`}
                    >
                      <p className="font-mono text-[11px] uppercase tracking-[0.24em] opacity-65">
                        {turn.role === "user" ? "Prompt" : "Response"}
                      </p>
                      <p className="mt-3 whitespace-pre-wrap text-[15px] leading-7">{turn.content}</p>

                      {turn.role === "assistant" && turn.citations?.length ? (
                        <div className="mt-5 space-y-3 border-t border-stone-300/80 pt-4">
                          {turn.citations.map((citation, citationIndex) => (
                            <div
                              key={`${citation.title}-${citationIndex}`}
                              className="rounded-[1.3rem] border border-stone-300 bg-white/70 px-4 py-4"
                            >
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-stone-500">
                                  {citation.ticker}
                                </span>
                                <span className="text-xs text-stone-400">/</span>
                                <span className="text-xs text-stone-500">{citation.source_type}</span>
                                {citation.event_type ? <span className="text-xs text-stone-400">/ {citation.event_type}</span> : null}
                              </div>
                              <p className="mt-2 text-sm font-medium leading-6 text-stone-900">
                                {citation.title}
                              </p>
                              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-500">
                                {citation.sentiment_label ? (
                                  <span className={sentimentTone(citation.sentiment_label)}>
                                    Sentiment: {citation.sentiment_label}
                                    {citation.sentiment_score != null ? ` (${citation.sentiment_score.toFixed(2)})` : ""}
                                  </span>
                                ) : null}
                                {citation.impact_label ? <span>Impact: {citation.impact_label}</span> : null}
                                {citation.similarity_score != null ? (
                                  <span>Relevance: {citation.similarity_score.toFixed(2)}</span>
                                ) : null}
                                {citation.published_at ? (
                                  <span>{new Date(citation.published_at).toLocaleDateString("en-IN")}</span>
                                ) : null}
                              </div>
                              <p className="mt-3 text-sm leading-6 text-stone-600">{citation.snippet}</p>
                              {citation.url ? (
                                <a
                                  className="mt-3 inline-flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-stone-700 transition hover:text-stone-950"
                                  href={citation.url}
                                  rel="noreferrer"
                                  target="_blank"
                                >
                                  Open source
                                  <ArrowUpRight className="size-3" />
                                </a>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </AuthGuard>
  )
}

function Metric({
  label,
  value,
  valueClassName,
}: {
  label: string
  value: string
  valueClassName?: string
}) {
  return (
    <div className="space-y-0.5">
      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-stone-500">{label}</p>
      <p className={`text-base font-medium text-stone-900 ${valueClassName ?? ""}`}>{value}</p>
    </div>
  )
}

function Notice({ tone, message }: { tone: "success" | "error"; message: string }) {
  const classes =
    tone === "success"
      ? "border-emerald-700/25 bg-emerald-50/70 text-emerald-800"
      : "border-rose-700/20 bg-rose-50/70 text-rose-700"

  return <p className={`rounded-[1.2rem] border px-4 py-3 text-sm ${classes}`}>{message}</p>
}

function getErrorMessage(error: unknown, fallback: string) {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof error.response === "object" &&
    error.response !== null &&
    "data" in error.response &&
    typeof error.response.data === "object" &&
    error.response.data !== null &&
    "detail" in error.response.data &&
    typeof error.response.data.detail === "string"
  ) {
    return error.response.data.detail
  }

  return fallback
}
