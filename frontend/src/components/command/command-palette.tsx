"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { MessageSquare, Search, Star, TrendingUp } from "lucide-react"

import { Dialog, DialogContent } from "@/components/ui/dialog"
import { navItems } from "@/config/navigation"
import { relativeTime } from "@/lib/format"
import { listFollowedStocks } from "@/services/stocks"
import { listSessions } from "@/services/research"
import { useStockDetailStore } from "@/store/stock-detail-store"
import { useUiStore } from "@/store/ui-store"

type PaletteItem = {
  id: string
  label: string
  sublabel?: string
  icon: React.ReactNode
  onSelect: () => void
}

export function CommandPalette() {
  const open = useUiStore((state) => state.commandPaletteOpen)
  const setOpen = useUiStore((state) => state.setCommandPaletteOpen)
  const openStockDetail = useStockDetailStore((state) => state.open)
  const router = useRouter()
  const [query, setQuery] = useState("")
  const [wasOpen, setWasOpen] = useState(open)

  // Clear the search box once the palette closes -- adjusted during render
  // (React's documented pattern) rather than an Effect, since it's purely
  // derived from `open` transitioning, not a subscription to anything external.
  if (open !== wasOpen) {
    setWasOpen(open)
    if (!open) setQuery("")
  }

  const stocksQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks, enabled: open })
  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: listSessions, enabled: open })

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setOpen(!open)
      }
      if (event.key === "Escape") setOpen(false)
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [open, setOpen])

  const items = useMemo<PaletteItem[]>(() => {
    const pages: PaletteItem[] = navItems.map((item) => ({
      id: `page-${item.href}`,
      label: item.label,
      sublabel: "Page",
      icon: <item.icon className="size-4" />,
      onSelect: () => router.push(item.href),
    }))

    const stocks: PaletteItem[] = (stocksQuery.data ?? []).map((followed) => ({
      id: `stock-${followed.stock.ticker}`,
      label: followed.stock.ticker,
      sublabel: followed.stock.company_name,
      icon: <TrendingUp className="size-4" />,
      onSelect: () => openStockDetail(followed.stock.ticker),
    }))

    const sessions: PaletteItem[] = (sessionsQuery.data ?? []).slice(0, 8).map((session) => ({
      id: `session-${session.id}`,
      label: session.title,
      sublabel: `Chat · ${relativeTime(session.updated_at)}`,
      icon: <MessageSquare className="size-4" />,
      onSelect: () => router.push(`/chat?session=${session.id}`),
    }))

    return [...pages, ...stocks, ...sessions]
  }, [stocksQuery.data, sessionsQuery.data, router, openStockDetail])

  const filtered = useMemo(() => {
    const trimmed = query.trim().toLowerCase()
    if (!trimmed) return items
    return items.filter(
      (item) => item.label.toLowerCase().includes(trimmed) || item.sublabel?.toLowerCase().includes(trimmed)
    )
  }, [items, query])

  function select(item: PaletteItem) {
    item.onSelect()
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent showClose={false} className="top-[18%] max-w-lg translate-y-0 gap-0 overflow-hidden p-0">
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Jump to a page, followed stock, or past chat…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="shrink-0 rounded border border-border bg-muted px-1 font-mono text-[10px] text-muted-foreground">
            Esc
          </kbd>
        </div>

        <div className="max-h-80 overflow-y-auto p-2">
          {filtered.length === 0 && (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">No matches.</p>
          )}
          {filtered.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => select(item)}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-accent"
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                {item.icon}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{item.label}</span>
                {item.sublabel && <span className="block truncate text-xs text-muted-foreground">{item.sublabel}</span>}
              </span>
            </button>
          ))}
        </div>

        <div className="hidden items-center gap-3 border-t border-border px-4 py-2 text-[11px] text-muted-foreground sm:flex">
          <span className="inline-flex items-center gap-1">
            <Star className="size-3" /> Followed stocks open the detail drawer
          </span>
        </div>
      </DialogContent>
    </Dialog>
  )
}
