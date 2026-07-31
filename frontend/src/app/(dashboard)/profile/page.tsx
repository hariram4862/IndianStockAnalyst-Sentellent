"use client"

import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { LogOut } from "lucide-react"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { initialsFromName, relativeTime } from "@/lib/format"
import { getPersona } from "@/services/research"
import { useAuthStore } from "@/store/auth-store"

export default function ProfilePage() {
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const personaQuery = useQuery({ queryKey: ["persona"], queryFn: getPersona })
  const persona = personaQuery.data

  function handleLogout() {
    logout()
    router.replace("/login")
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-2xl space-y-8">
        <div>
          <h1 className="text-lg font-semibold">Profile</h1>
          <p className="text-sm text-muted-foreground">Your account and what the agent has learned about you.</p>
        </div>

        <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-4">
          <div className="flex items-center gap-3">
            <Avatar size="lg">
              <AvatarImage src={user?.profile_picture} alt={user?.full_name} />
              <AvatarFallback>{initialsFromName(user?.full_name)}</AvatarFallback>
            </Avatar>
            <div>
              <p className="font-medium">{user?.full_name}</p>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
            </div>
          </div>
          <Button variant="outline" onClick={handleLogout} className="gap-2">
            <LogOut className="size-4" /> Log out
          </Button>
        </div>

        <div className="space-y-3 rounded-lg border border-border p-4">
          <div>
            <h2 className="text-sm font-semibold">Investor persona</h2>
            <p className="text-xs text-muted-foreground">
              Learned automatically from what you tell the agent in chat.
            </p>
          </div>

          {personaQuery.isLoading && (
            <div className="space-y-2">
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-16 w-full" />
            </div>
          )}

          {!personaQuery.isLoading && !persona?.summary && (
            <p className="text-sm text-muted-foreground">
              Nothing learned yet — tell the agent things like &quot;I&apos;m a conservative,
              dividend-focused investor and I avoid high-debt companies&quot; in chat.
            </p>
          )}

          {persona?.summary && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {persona.risk_profile && <Badge variant="default">{persona.risk_profile}</Badge>}
                {persona.investment_style && <Badge variant="outline">{persona.investment_style}</Badge>}
              </div>
              <p className="text-sm text-muted-foreground">{persona.summary}</p>
              {persona.constraints_text && (
                <p className="text-sm">
                  <span className="font-medium">Constraint: </span>
                  <span className="text-muted-foreground">{persona.constraints_text}</span>
                </p>
              )}
              {persona.updated_at && (
                <p className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
                  Updated {relativeTime(persona.updated_at)}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
