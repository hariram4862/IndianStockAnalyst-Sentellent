"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { LogOut, Menu, Plus, Search } from "lucide-react"

import { navItems } from "@/config/navigation"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { FollowTickerDialog } from "@/components/stocks/follow-ticker-dialog"
import { cn } from "@/lib/utils"
import { initialsFromName } from "@/lib/format"
import { useAuthStore } from "@/store/auth-store"
import { useUiStore } from "@/store/ui-store"

function useCurrentPageTitle() {
  const pathname = usePathname()
  const match = navItems.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))
  return match?.label ?? "Indian Stock Analyst"
}

export default function Topbar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const setCommandPaletteOpen = useUiStore((state) => state.setCommandPaletteOpen)
  const title = useCurrentPageTitle()

  function handleLogout() {
    setMobileOpen(false)
    logout()
    router.replace("/login")
  }

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-border bg-background/85 px-4 py-3 backdrop-blur-sm sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="flex size-8 shrink-0 items-center justify-center rounded-md hover:bg-accent lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="size-5" />
        </button>
        <h1 className="truncate text-sm font-semibold sm:text-base">{title}</h1>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={() => setCommandPaletteOpen(true)}
          className="hidden items-center gap-2 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:border-accent-brand/40 hover:text-foreground sm:flex"
        >
          <Search className="size-3.5" />
          Search
          <kbd className="rounded border border-border bg-muted px-1 font-mono text-[10px]">⌘K</kbd>
        </button>
        <FollowTickerDialog
          trigger={
            <Button size="sm" className="gap-1.5">
              <Plus className="size-4" />
              <span className="hidden sm:inline">Follow ticker</span>
            </Button>
          }
        />
      </div>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="max-w-[280px] sm:max-w-[280px]">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <span className="flex size-7 items-center justify-center rounded-md bg-accent-brand font-mono text-xs font-semibold text-accent-brand-foreground">
                IA
              </span>
              Indian Stock Analyst
            </SheetTitle>
          </SheetHeader>

          <nav className="flex flex-1 flex-col gap-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = pathname === item.href
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary text-primary-foreground"
                      : "text-foreground/80 hover:bg-accent"
                  )}
                >
                  <Icon className="size-4" />
                  {item.label}
                </Link>
              )
            })}
          </nav>

          <div className="mt-auto space-y-2 border-t border-border pt-4">
            <div className="flex items-center gap-2 px-1">
              <Avatar size="sm">
                <AvatarImage src={user?.profile_picture} alt={user?.full_name} />
                <AvatarFallback>{initialsFromName(user?.full_name)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{user?.full_name ?? "Account"}</p>
                <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-foreground/80 hover:bg-accent"
            >
              <LogOut className="size-4" /> Log out
            </button>
          </div>
        </SheetContent>
      </Sheet>
    </header>
  )
}
