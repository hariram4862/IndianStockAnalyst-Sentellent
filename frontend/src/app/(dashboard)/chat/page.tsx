"use client"

import { Suspense, useEffect, useRef, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AnimatePresence, motion } from "framer-motion"
import { toast } from "sonner"
import { ArrowDown, History, Send, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { AssistantMessage } from "@/components/chat/assistant-message"
import { MessageSources } from "@/components/chat/citation-list"
import { RecommendationCards } from "@/components/chat/recommendation-cards"
import { SessionList } from "@/components/chat/session-list"
import { getErrorMessage } from "@/lib/errors"
import { cn } from "@/lib/utils"
import { getSessionMessages, listSessions, sendResearchMessage } from "@/services/research"
import { listFollowedStocks } from "@/services/stocks"
import type { ChatMessage } from "@/types/research"

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageContent />
    </Suspense>
  )
}

function ChatPageContent() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const searchParams = useSearchParams()

  // Lazily seeded from ?session= / ?prompt= (set by Overview, the Stock Detail
  // Drawer, or the command palette) -- read once at mount, not reactively.
  const [activeSessionId, setActiveSessionId] = useState<number | null>(() => {
    const sessionParam = searchParams.get("session")
    return sessionParam ? Number(sessionParam) : null
  })
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState(() => searchParams.get("prompt") ?? "")
  const [personaSummary, setPersonaSummary] = useState<string | null>(null)
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [animateIndex, setAnimateIndex] = useState<number | null>(null)

  const scrollRef = useRef<HTMLDivElement>(null)

  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: listSessions })
  const stocksQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })

  const historyQuery = useQuery({
    queryKey: ["session-messages", activeSessionId],
    queryFn: () => getSessionMessages(activeSessionId as number),
    enabled: activeSessionId != null,
  })

  // Strip the one-shot ?session=/?prompt= params from the URL once consumed
  // by the lazy state initializers above -- no state to set here, just a
  // navigation side effect, so it doesn't fall under set-state-in-effect.
  useEffect(() => {
    if (searchParams.get("session") || searchParams.get("prompt")) {
      router.replace("/chat")
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Mirrors react-query's session-history cache into local state so sent
  // messages can be appended optimistically on top of it; justified effect
  // (syncing from an external cache), not state derivable during render.
  useEffect(() => {
    if (activeSessionId != null && historyQuery.data) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMessages(historyQuery.data)
      setAnimateIndex(null)
    }
  }, [activeSessionId, historyQuery.data])

  useEffect(() => {
    if (!autoScroll) return
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, autoScroll])

  const sendMutation = useMutation({
    mutationFn: (message: string) => sendResearchMessage(message, activeSessionId),
    onMutate: (message) => {
      setMessages((current) => [
        ...current,
        { role: "user", content: message, citations: [], created_at: new Date().toISOString() },
      ])
      setAutoScroll(true)
    },
    onSuccess: (data) => {
      setMessages((current) => {
        const next: ChatMessage[] = [
          ...current,
          {
            role: "assistant",
            content: data.answer,
            citations: data.citations,
            intent: data.intent,
            ranked_stocks: data.ranked_stocks,
            created_at: new Date().toISOString(),
          },
        ]
        setAnimateIndex(next.length - 1)
        return next
      })
      setActiveSessionId(data.session_id)
      setPersonaSummary(data.persona_summary)
      queryClient.invalidateQueries({ queryKey: ["sessions"] })
    },
    onError: (error) => {
      setMessages((current) => current.slice(0, -1))
      toast.error(getErrorMessage(error, "Could not send message."))
    },
  })

  function handleNewChat() {
    setActiveSessionId(null)
    setMessages([])
    setPersonaSummary(null)
    setAnimateIndex(null)
  }

  function handleSelectSession(id: number) {
    setActiveSessionId(id)
    setMobileHistoryOpen(false)
  }

  function handleSend(overrideMessage?: string) {
    const trimmed = (overrideMessage ?? input).trim()
    if (!trimmed || sendMutation.isPending) return
    setInput("")
    sendMutation.mutate(trimmed)
  }

  function handleScroll() {
    const el = scrollRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    setAutoScroll(distanceFromBottom < 80)
  }

  const followedTickers = (stocksQuery.data ?? []).slice(0, 3).map((f) => f.stock.ticker)
  const suggestedPrompts = [
    ...followedTickers.map((ticker) => `What's the sentiment on ${ticker} this week?`),
    "Recommend stocks for my profile",
  ]

  return (
    <div className="grid h-full grid-cols-1 lg:grid-cols-[260px_1fr]">
      <aside className="hidden overflow-hidden border-r border-sidebar-border bg-sidebar lg:block">
        <SessionList
          sessions={sessionsQuery.data ?? []}
          activeSessionId={activeSessionId}
          isLoading={sessionsQuery.isLoading}
          onSelect={handleSelectSession}
          onNewChat={handleNewChat}
          onDeletedActive={handleNewChat}
        />
      </aside>

      <div className="relative flex min-w-0 flex-col overflow-hidden">
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6 sm:py-4">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold sm:text-base">Research chat</h2>
            <p className="hidden text-xs text-muted-foreground sm:block">
              Ask about a stock you follow, or say &quot;recommend stocks for my profile.&quot;
            </p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5 lg:hidden" onClick={() => setMobileHistoryOpen(true)}>
            <History className="size-3.5" /> History
          </Button>
        </header>

        {personaSummary && (
          <div className="mx-4 mt-3 rounded-lg border border-border bg-muted/50 px-4 py-2 text-sm text-muted-foreground sm:mx-6">
            <span className="font-medium text-foreground">Investor memory: </span>
            {personaSummary}
          </div>
        )}

        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="mx-auto w-full max-w-3xl flex-1 space-y-5 overflow-y-auto px-4 py-4 sm:px-6"
        >
          {historyQuery.isLoading && activeSessionId != null && (
            <div className="space-y-3">
              <Skeleton className="h-16 w-2/3" />
              <Skeleton className="ml-auto h-16 w-2/3" />
            </div>
          )}

          {messages.length === 0 && !historyQuery.isLoading && (
            <div className="flex h-full flex-col items-center justify-center gap-4 py-10 text-center">
              <Sparkles className="size-6 text-accent-brand" />
              <div>
                <p className="text-sm font-medium">Ask your first research question</p>
                <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
                  Every answer is grounded in your ingested fundamentals and news, with citations.
                </p>
              </div>
              {suggestedPrompts.length > 0 && (
                <div className="flex max-w-md flex-wrap justify-center gap-2">
                  {suggestedPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => handleSend(prompt)}
                      className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-accent-brand/50 hover:text-foreground"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((message, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={cn("max-w-[92%] sm:max-w-[85%]", message.role === "user" ? "ml-auto" : "mr-auto w-full")}
            >
              {message.role === "user" ? (
                <div className="rounded-lg border border-transparent bg-primary px-4 py-3 text-sm whitespace-pre-wrap text-primary-foreground">
                  {message.content}
                </div>
              ) : (
                <div className="rounded-lg border border-border bg-card px-4 py-3">
                  <AssistantMessage content={message.content} messageKey={index} animate={index === animateIndex} />
                </div>
              )}

              {message.role === "assistant" &&
                message.intent === "recommend" &&
                (message.ranked_stocks?.length ?? 0) > 0 && (
                  <div className="mt-3">
                    <RecommendationCards picks={message.ranked_stocks ?? []} />
                  </div>
                )}

              {message.role === "assistant" && (
                <MessageSources
                  citations={message.citations}
                  messageKey={index}
                  defaultOpen={message.citations.length > 0 && message.citations.length <= 3}
                />
              )}
            </motion.div>
          ))}

          <AnimatePresence>
            {sendMutation.isPending && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="mr-auto flex w-fit items-center gap-1 rounded-lg border border-border bg-card px-4 py-3"
              >
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    className="size-1.5 rounded-full bg-muted-foreground"
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {!autoScroll && messages.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setAutoScroll(true)
              scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
            }}
            className="absolute bottom-24 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-xs shadow-md transition-colors hover:border-accent-brand/40"
          >
            <ArrowDown className="size-3.5" /> Jump to latest
          </button>
        )}

        <div className="border-t border-border p-3 sm:p-4">
          <div className="mx-auto flex max-w-3xl items-end gap-2">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  handleSend()
                }
              }}
              placeholder="What's the sentiment on TCS this week?"
              className="min-h-11"
            />
            <Button onClick={() => handleSend()} disabled={sendMutation.isPending || !input.trim()} size="icon">
              <Send className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      <Sheet open={mobileHistoryOpen} onOpenChange={setMobileHistoryOpen}>
        <SheetContent side="left" className="max-w-[280px] p-0 sm:max-w-[280px]">
          <SheetHeader className="p-4 pr-10">
            <SheetTitle>Chat history</SheetTitle>
          </SheetHeader>
          <SessionList
            sessions={sessionsQuery.data ?? []}
            activeSessionId={activeSessionId}
            isLoading={sessionsQuery.isLoading}
            onSelect={handleSelectSession}
            onNewChat={() => {
              handleNewChat()
              setMobileHistoryOpen(false)
            }}
            onDeletedActive={handleNewChat}
          />
        </SheetContent>
      </Sheet>
    </div>
  )
}
