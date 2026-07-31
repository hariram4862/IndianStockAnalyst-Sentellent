import Link from "next/link"

import { cn } from "@/lib/utils"
import type { NavItem } from "@/config/navigation"

interface SidebarItemProps {
  item: NavItem
  active?: boolean
}

export default function SidebarItem({ item, active }: SidebarItemProps) {
  const Icon = item.icon

  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-sidebar-primary text-sidebar-primary-foreground"
          : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
      )}
    >
      <Icon className="size-4" />
      {item.label}
    </Link>
  )
}
