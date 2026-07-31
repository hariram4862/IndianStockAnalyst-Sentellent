import type { ComponentType } from "react"
import { LayoutDashboard, MessageSquare, Star, User } from "lucide-react"

export interface NavItem {
  label: string
  href: string
  icon: ComponentType<{ className?: string }>
}

export const navItems: NavItem[] = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { label: "Chat", href: "/chat", icon: MessageSquare },
  { label: "Watchlist", href: "/watchlist", icon: Star },
  { label: "Profile", href: "/profile", icon: User },
]
