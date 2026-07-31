"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { useTheme } from "next-themes"
import { ChevronsLeft, ChevronsRight, LogOut, Monitor, Moon, Sun, SunMoon, User as UserIcon } from "lucide-react"

import { navItems } from "@/config/navigation"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { initialsFromName } from "@/lib/format"
import { useAuthStore } from "@/store/auth-store"
import { useUiStore } from "@/store/ui-store"

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const { sidebarCollapsed, toggleSidebar } = useUiStore()
  const { theme, setTheme } = useTheme()

  function handleLogout() {
    logout()
    router.replace("/login")
  }

  return (
    <aside
      className={cn(
        "hidden h-svh shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-200 lg:flex",
        sidebarCollapsed ? "w-[68px]" : "w-64"
      )}
    >
      <div className={cn("flex items-center gap-2 px-5 py-5", sidebarCollapsed && "justify-center px-0")}>
        <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-accent-brand font-mono text-sm font-semibold text-accent-brand-foreground">
          IA
        </div>
        {!sidebarCollapsed && (
          <span className="truncate text-sm font-medium text-sidebar-foreground">Indian Stock Analyst</span>
        )}
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {navItems.map((item) => {
          const active = pathname === item.href
          const Icon = item.icon
          const link = (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                sidebarCollapsed && "justify-center px-0",
                active
                  ? "text-sidebar-primary-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              )}
            >
              {active && (
                <motion.span
                  layoutId="sidebar-active-pill"
                  className="absolute inset-0 rounded-lg bg-sidebar-primary"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
              <Icon className="relative z-10 size-4 shrink-0" />
              {!sidebarCollapsed && <span className="relative z-10 truncate">{item.label}</span>}
            </Link>
          )

          if (!sidebarCollapsed) return link

          return (
            <Tooltip key={item.href}>
              <TooltipTrigger render={link} />
              <TooltipContent side="right">{item.label}</TooltipContent>
            </Tooltip>
          )
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <DropdownMenu>
          <DropdownMenuTrigger
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left outline-none hover:bg-sidebar-accent",
              sidebarCollapsed && "justify-center px-0"
            )}
          >
            <Avatar size="sm">
              <AvatarImage src={user?.profile_picture} alt={user?.full_name} />
              <AvatarFallback>{initialsFromName(user?.full_name)}</AvatarFallback>
            </Avatar>
            {!sidebarCollapsed && (
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-sidebar-foreground">
                  {user?.full_name ?? "Account"}
                </p>
                <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
              </div>
            )}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" side="top" className="w-56">
            {/* Base UI requires GroupLabel to have a Group ancestor, even a
                lone one -- omitting this throws and blanks the whole menu. */}
            <DropdownMenuGroup>
              <DropdownMenuLabel>Signed in as {user?.email}</DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            {/* Rendered as a real <Link> (not an imperative router.push in
                onClick) so navigation is a normal anchor click and doesn't
                depend on the menu's close/unmount timing. */}
            <DropdownMenuItem render={<Link href="/profile" />}>
              <UserIcon /> Profile
            </DropdownMenuItem>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger>
                <SunMoon /> Appearance
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuRadioGroup value={theme} onValueChange={setTheme}>
                  <DropdownMenuRadioItem value="system">
                    <Monitor /> System
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="light">
                    <Sun /> Light
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="dark">
                    <Moon /> Dark
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={handleLogout}>
              <LogOut /> Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <button
          type="button"
          onClick={toggleSidebar}
          className={cn(
            "mt-2 flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground",
            sidebarCollapsed && "justify-center"
          )}
        >
          {sidebarCollapsed ? <ChevronsRight className="size-4" /> : <ChevronsLeft className="size-4" />}
          {!sidebarCollapsed && "Collapse"}
        </button>
      </div>
    </aside>
  )
}
