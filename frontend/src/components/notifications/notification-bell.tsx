"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Bell } from "lucide-react"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { relativeTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import { listNotifications, markNotificationsRead } from "@/services/alerts"

export function NotificationBell() {
  const queryClient = useQueryClient()
  const notificationsQuery = useQuery({ queryKey: ["notifications"], queryFn: listNotifications })
  const notifications = notificationsQuery.data ?? []
  const unreadCount = notifications.filter((n) => !n.is_read).length

  const markReadMutation = useMutation({
    mutationFn: markNotificationsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  })

  return (
    <DropdownMenu
      onOpenChange={(open) => {
        if (open && unreadCount > 0) markReadMutation.mutate()
      }}
    >
      <DropdownMenuTrigger
        className="relative flex size-8 items-center justify-center rounded-lg text-muted-foreground outline-none hover:bg-accent hover:text-foreground"
        aria-label="Notifications"
      >
        <Bell className="size-4" />
        {unreadCount > 0 && <span className="absolute top-1 right-1 flex size-2 rounded-full bg-negative" />}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Alerts</DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 && (
            <p className="px-2 py-4 text-center text-sm text-muted-foreground">
              No alerts yet. Set one from a stock&apos;s detail panel.
            </p>
          )}
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className={cn(
                "space-y-0.5 rounded-md px-2 py-2 text-sm",
                !notification.is_read && "bg-accent"
              )}
            >
              <p className="font-medium">{notification.ticker}</p>
              <p className="text-xs text-muted-foreground">{notification.message}</p>
              <p className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
                {relativeTime(notification.created_at)}
              </p>
            </div>
          ))}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
