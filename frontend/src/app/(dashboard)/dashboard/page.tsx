"use client"

import { useEffect, useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { CitationList } from "@/components/chat/citation-list"
import { SessionList } from "@/components/chat/session-list"
import { getErrorMessage } from "@/lib/errors"
import { cn } from "@/lib/utils"
import { getSessionMessages, listSessions, sendResearchMessage } from "@/services/research"
import type { ChatMessage } from "@/types/research"

export default function ChatPage() {
  const queryClient = useQueryClient()
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [personaSummary, setPersonaSummary] = useState<string | null>(null)

  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: listSessions })

  const historyQuery = useQuery({
    queryKey: ["session-messages", activeSessionId],
    queryFn: () => getSessionMessages(activeSessionId as number),
    enabled: activeSessionId != null,
  })

  useEffect(() => {
    if (activeSessionId != null && historyQuery.data) {
      setMessages(historyQuery.data)
    }
  }, [activeSessionId, historyQuery.data])

  const sendMutation = useMutation({
    mutationFn: (message: string) => sendResearchMessage(message, activeSessionId),
    onMutate: (message) => {
      setMessages((current) => [
        ...current,
        { role: "user", content: message, citations: [], created_at: new Date().toISOString() },
      ])
    },
    onSuccess: (data) => {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.answer,
          citations: data.citations,
          created_at: new Date().toISOString(),
        },
      ])
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
  }

  function handleSend() {
    const trimmed = input.trim()
    if (!trimmed || sendMutation.isPending) return
    setInput("")
    sendMutation.mutate(trimmed)
  }

  const lastAssistantMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant"),
    [messages]
  )

  return (
    <div className="grid h-full grid-cols-1 lg:grid-cols-[240px_1fr] xl:grid-cols-[240px_1fr_320px]">
      <aside className="hidden overflow-hidden border-r border-border lg:block">
        <SessionList
          sessions={sessionsQuery.data ?? []}
          activeSessionId={activeSessionId}
          isLoading={sessionsQuery.isLoading}
          onSelect={setActiveSessionId}
          onNewChat={handleNewChat}
        />
      </aside>

      <div className="flex min-w-0 flex-col overflow-hidden">
        <header className="border-b border-border px-6 py-4">
          <h1 className="text-lg font-semibold">Research chat</h1>
          <p className="text-sm text-muted-foreground">
            Ask about a stock you follow, or say &quot;recommend stocks for my profile.&quot;
          </p>
        </header>

        {personaSummary && (
          <div className="mx-6 mt-4 rounded-lg border border-border bg-muted/50 px-4 py-2 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Investor memory: </span>
            {personaSummary}
          </div>
        )}

        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
          {historyQuery.isLoading && activeSessionId != null && (
            <div className="space-y-3">
              <Skeleton className="h-16 w-2/3" />
              <Skeleton className="ml-auto h-16 w-2/3" />
            </div>
          )}

          {messages.length === 0 && !historyQuery.isLoading && (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
              <p className="text-sm font-medium">Ask your first research question</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Try &quot;What&apos;s the sentiment on RELIANCE this week?&quot; once you&apos;re following a
                stock.
              </p>
            </div>
          )}

          {messages.map((message, index) => (
            <div key={index} className={cn("max-w-[75%]", message.role === "user" ? "ml-auto" : "mr-auto")}>
              <div
                className={cn(
                  "rounded-lg border px-4 py-3 text-sm whitespace-pre-wrap",
                  message.role === "user"
                    ? "border-transparent bg-primary text-primary-foreground"
                    : "border-border bg-card"
                )}
              >
                {message.content}
              </div>
              {message.role === "assistant" && message.citations.length > 0 && (
                <div className="mt-2 xl:hidden">
                  <CitationList citations={message.citations} />
                </div>
              )}
            </div>
          ))}

          {sendMutation.isPending && (
            <div className="mr-auto max-w-[75%] rounded-lg border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
              Thinking…
            </div>
          )}
        </div>

        <div className="border-t border-border p-4">
          <div className="flex items-end gap-2">
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
            <Button onClick={handleSend} disabled={sendMutation.isPending || !input.trim()} size="icon">
              <Send className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      <aside className="hidden overflow-hidden border-l border-border xl:flex xl:flex-col">
        <div className="border-b border-border px-4 py-4">
          <h2 className="text-sm font-semibold">Sources</h2>
          <p className="text-xs text-muted-foreground">Evidence behind the latest answer.</p>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {lastAssistantMessage ? (
            <CitationList citations={lastAssistantMessage.citations} />
          ) : (
            <p className="text-sm text-muted-foreground">Ask a question to see grounded sources here.</p>
          )}
        </div>
      </aside>
    </div>
  )
}
