"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { toast } from "sonner"
import { LogOut, RotateCcw, Sparkles } from "lucide-react"

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
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { getErrorMessage } from "@/lib/errors"
import { initialsFromName, relativeTime } from "@/lib/format"
import { getPersona, resetPersona, listSessions } from "@/services/research"
import { listFollowedStocks } from "@/services/stocks"
import { useAuthStore } from "@/store/auth-store"
import { useOnboardingStore } from "@/store/onboarding-store"

function StatTile({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border p-3 text-center">
      <p className="text-xl font-semibold">{value}</p>
      <p className="mt-0.5 text-[11px] tracking-wide text-muted-foreground uppercase">{label}</p>
    </div>
  )
}

export default function ProfilePage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { user, logout } = useAuthStore()
  const restartOnboarding = useOnboardingStore((state) => state.start)
  const [confirmingReset, setConfirmingReset] = useState(false)

  const personaQuery = useQuery({ queryKey: ["persona"], queryFn: getPersona })
  const stocksQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })
  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: listSessions })
  const persona = personaQuery.data

  const resetMutation = useMutation({
    mutationFn: resetPersona,
    onSuccess: () => {
      toast.success("Investor memory reset.")
      queryClient.invalidateQueries({ queryKey: ["persona"] })
      setConfirmingReset(false)
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not reset memory.")),
  })

  function handleLogout() {
    logout()
    router.replace("/login")
  }

  return (
    <div className="h-full overflow-y-auto px-4 py-6 sm:px-6 sm:py-8">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mx-auto max-w-2xl space-y-8"
      >
        <div>
          <h1 className="text-lg font-semibold">Profile</h1>
          <p className="text-sm text-muted-foreground">Your account and what the agent has learned about you.</p>
        </div>

        <div className="flex flex-col gap-4 rounded-lg border border-border p-4 sm:flex-row sm:items-center sm:justify-between">
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

        <div className="grid grid-cols-3 gap-3">
          <StatTile label="Stocks followed" value={stocksQuery.isLoading ? "—" : (stocksQuery.data ?? []).length} />
          <StatTile label="Chat sessions" value={sessionsQuery.isLoading ? "—" : (sessionsQuery.data ?? []).length} />
          <StatTile label="Risk profile" value={persona?.risk_profile ?? "—"} />
        </div>

        <div className="space-y-3 rounded-lg border border-border p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Investor persona</h2>
              <p className="text-xs text-muted-foreground">
                Learned automatically from what you tell the agent in chat.
              </p>
            </div>
            {persona?.summary && (
              <Button variant="ghost" size="sm" className="shrink-0 gap-1.5" onClick={() => setConfirmingReset(true)}>
                <RotateCcw className="size-3.5" /> Reset
              </Button>
            )}
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
                {persona.risk_profile && <Badge variant="accent">{persona.risk_profile}</Badge>}
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

        <button
          type="button"
          onClick={restartOnboarding}
          className="flex w-full items-center justify-between rounded-lg border border-dashed border-border p-4 text-left transition-colors hover:border-accent-brand/40"
        >
          <span>
            <span className="flex items-center gap-1.5 text-sm font-medium">
              <Sparkles className="size-4 text-accent-brand" /> Replay the quick tour
            </span>
            <span className="mt-0.5 block text-xs text-muted-foreground">
              See the follow → ask → cited-answer walkthrough again.
            </span>
          </span>
        </button>
      </motion.div>

      <AlertDialog open={confirmingReset} onOpenChange={setConfirmingReset}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset investor memory?</AlertDialogTitle>
            <AlertDialogDescription>
              This clears everything the agent has learned about your risk profile, investment style, and
              constraints. It will start learning fresh from your next messages.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setConfirmingReset(false)}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => resetMutation.mutate()} disabled={resetMutation.isPending}>
              Reset
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
