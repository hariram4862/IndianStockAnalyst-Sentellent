"use client"

import { useMemo, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Check, MoreHorizontal, Pencil, Plus, Search, Trash2, X } from "lucide-react"

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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { getErrorMessage } from "@/lib/errors"
import { relativeTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import { deleteSession, renameSession } from "@/services/research"
import type { ChatSessionSummary } from "@/types/research"

interface SessionListProps {
  sessions: ChatSessionSummary[]
  activeSessionId: number | null
  isLoading: boolean
  onSelect: (id: number) => void
  onNewChat: () => void
  onDeletedActive: () => void
}

export function SessionList({
  sessions,
  activeSessionId,
  isLoading,
  onSelect,
  onNewChat,
  onDeletedActive,
}: SessionListProps) {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState("")
  const [renamingId, setRenamingId] = useState<number | null>(null)
  const [renameValue, setRenameValue] = useState("")
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const filtered = useMemo(() => {
    const trimmed = search.trim().toLowerCase()
    if (!trimmed) return sessions
    return sessions.filter((session) => session.title.toLowerCase().includes(trimmed))
  }, [sessions, search])

  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: number; title: string }) => renameSession(id, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] })
      setRenamingId(null)
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not rename session.")),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteSession(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] })
      if (id === activeSessionId) onDeletedActive()
      setDeletingId(null)
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not delete session.")),
  })

  function startRename(session: ChatSessionSummary) {
    setRenamingId(session.id)
    setRenameValue(session.title)
  }

  function commitRename(id: number) {
    const trimmed = renameValue.trim()
    if (!trimmed) {
      setRenamingId(null)
      return
    }
    renameMutation.mutate({ id, title: trimmed })
  }

  return (
    <div className="flex h-full flex-col">
      <div className="space-y-2 p-3">
        <Button onClick={onNewChat} variant="outline" className="w-full justify-start gap-2">
          <Plus className="size-4" /> New chat
        </Button>
        {sessions.length > 3 && (
          <div className="relative">
            <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search chats…"
              className="h-8 pl-8 text-xs"
            />
          </div>
        )}
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto px-3 pb-3">
        {isLoading &&
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-11 w-full" />)}

        {!isLoading && filtered.length === 0 && (
          <p className="px-2 py-4 text-sm text-muted-foreground">
            {search ? "No matching chats." : "No past research yet."}
          </p>
        )}

        {!isLoading &&
          filtered.map((session) => {
            const isActive = session.id === activeSessionId
            const isRenaming = renamingId === session.id

            if (isRenaming) {
              return (
                <div key={session.id} className="flex items-center gap-1 px-1">
                  <Input
                    autoFocus
                    value={renameValue}
                    onChange={(event) => setRenameValue(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") commitRename(session.id)
                      if (event.key === "Escape") setRenamingId(null)
                    }}
                    className="h-8 text-xs"
                  />
                  <Button size="icon-sm" variant="ghost" onClick={() => commitRename(session.id)}>
                    <Check className="size-3.5" />
                  </Button>
                  <Button size="icon-sm" variant="ghost" onClick={() => setRenamingId(null)}>
                    <X className="size-3.5" />
                  </Button>
                </div>
              )
            }

            return (
              <div
                key={session.id}
                className={cn(
                  "group relative flex items-center rounded-lg pr-1 transition-colors",
                  isActive ? "bg-primary text-primary-foreground" : "hover:bg-accent"
                )}
              >
                <button
                  type="button"
                  onClick={() => onSelect(session.id)}
                  className="min-w-0 flex-1 px-3 py-2 text-left text-sm"
                >
                  <p className="truncate font-medium">{session.title}</p>
                  <p className={cn("truncate text-xs", isActive ? "text-primary-foreground/70" : "text-muted-foreground")}>
                    {relativeTime(session.updated_at)}
                  </p>
                </button>
                <DropdownMenu>
                  <DropdownMenuTrigger
                    className={cn(
                      "flex size-7 shrink-0 items-center justify-center rounded-md opacity-0 outline-none group-hover:opacity-100 data-[popup-open]:opacity-100",
                      isActive ? "hover:bg-primary-foreground/10" : "hover:bg-muted"
                    )}
                  >
                    <MoreHorizontal className="size-3.5" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-36">
                    <DropdownMenuItem onClick={() => startRename(session)}>
                      <Pencil /> Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem variant="destructive" onClick={() => setDeletingId(session.id)}>
                      <Trash2 /> Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )
          })}
      </div>

      <AlertDialog open={deletingId != null} onOpenChange={(open) => !open && setDeletingId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this chat?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the conversation and its citations. This can&apos;t be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingId(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingId != null && deleteMutation.mutate(deletingId)}
              disabled={deleteMutation.isPending}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
