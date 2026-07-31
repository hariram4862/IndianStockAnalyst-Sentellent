"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { LogOut, Menu, X } from "lucide-react"

import { navItems } from "@/config/navigation"
import { useAuthStore } from "@/store/auth-store"
import { cn } from "@/lib/utils"

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()
  const router = useRouter()
  const { logout } = useAuthStore()

  function handleLogout() {
    setOpen(false)
    logout()
    router.replace("/login")
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background lg:hidden">
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-sm font-medium">Indian Stock Analyst</span>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="flex size-8 items-center justify-center rounded-md hover:bg-accent"
          aria-label="Toggle menu"
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {open && (
        <nav className="flex flex-col gap-1 border-t border-border p-3">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className={cn(
                "rounded-lg px-3 py-2 text-sm font-medium",
                pathname === item.href
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground/80 hover:bg-accent"
              )}
            >
              {item.label}
            </Link>
          ))}
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-foreground/80 hover:bg-accent"
          >
            <LogOut className="size-4" /> Log out
          </button>
        </nav>
      )}
    </header>
  )
}
