"use client"

import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { relativeTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { ChatSessionSummary } from "@/types/research"

interface SessionListProps {
  sessions: ChatSessionSummary[]
  activeSessionId: number | null
  isLoading: boolean
  onSelect: (id: number) => void
  onNewChat: () => void
}

export function SessionList({ sessions, activeSessionId, isLoading, onSelect, onNewChat }: SessionListProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <Button onClick={onNewChat} variant="outline" className="w-full justify-start gap-2">
          <Plus className="size-4" /> New chat
        </Button>
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto px-3 pb-3">
        {isLoading &&
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-11 w-full" />)}

        {!isLoading && sessions.length === 0 && (
          <p className="px-2 py-4 text-sm text-muted-foreground">No past research yet.</p>
        )}

        {!isLoading &&
          sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              onClick={() => onSelect(session.id)}
              className={cn(
                "block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors",
                session.id === activeSessionId
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground/80 hover:bg-accent"
              )}
            >
              <p className="truncate font-medium">{session.title}</p>
              <p
                className={cn(
                  "truncate text-xs",
                  session.id === activeSessionId ? "text-primary-foreground/70" : "text-muted-foreground"
                )}
              >
                {relativeTime(session.updated_at)}
              </p>
            </button>
          ))}
      </div>
    </div>
  )
}
