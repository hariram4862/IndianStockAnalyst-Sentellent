"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useMutation } from "@tanstack/react-query"
import { Send, Sparkles } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { getErrorMessage } from "@/lib/errors"
import { sendResearchMessage } from "@/services/research"

export function DashboardChatBox() {
  const router = useRouter()
  const [input, setInput] = useState("")

  const sendMutation = useMutation({
    mutationFn: (message: string) => sendResearchMessage(message, null),
    onSuccess: (response) => {
      router.push(`/chat?session=${response.session_id}`)
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not send that message.")),
  })

  function submit() {
    const message = input.trim()
    if (!message || sendMutation.isPending) return
    sendMutation.mutate(message)
  }

  return (
    <div className="space-y-2 rounded-xl border border-border p-4">
      <div className="flex items-center gap-1.5">
        <Sparkles className="size-4 text-accent-brand" />
        <h2 className="text-sm font-semibold">Ask the agent</h2>
      </div>
      <Textarea
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault()
            submit()
          }
        }}
        placeholder="e.g. How is HDFC Bank's debt position looking this quarter?"
        rows={2}
        disabled={sendMutation.isPending}
        className="resize-none"
      />
      <div className="flex justify-end">
        <Button size="sm" className="gap-1.5" onClick={submit} disabled={!input.trim() || sendMutation.isPending}>
          <Send className="size-3.5" /> {sendMutation.isPending ? "Starting…" : "Start chat"}
        </Button>
      </div>
    </div>
  )
}
