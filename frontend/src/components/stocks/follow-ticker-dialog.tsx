"use client"

import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { z } from "zod"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { SUGGESTED_TICKERS } from "@/config/tickers"
import { getErrorMessage } from "@/lib/errors"
import { followStock } from "@/services/stocks"

const followSchema = z.object({
  ticker: z
    .string()
    .trim()
    .min(1, "Enter a ticker")
    .max(15, "Ticker looks too long")
    .regex(/^[A-Za-z]+$/, "Letters only, e.g. RELIANCE"),
})

type FollowFormValues = z.infer<typeof followSchema>

export function FollowTickerDialog({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FollowFormValues>({
    resolver: zodResolver(followSchema),
    defaultValues: { ticker: "" },
  })

  const { onChange: onTickerChange, ...tickerField } = register("ticker")

  const followMutation = useMutation({
    mutationFn: (ticker: string) => followStock(ticker),
    onSuccess: (data) => {
      toast.success(data.message)
      queryClient.invalidateQueries({ queryKey: ["followed-stocks"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] })
      reset()
      setOpen(false)
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not follow ticker.")),
  })

  function onSubmit(values: FollowFormValues) {
    followMutation.mutate(values.ticker.trim().toUpperCase())
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) reset()
      }}
    >
      <DialogTrigger render={trigger as React.ReactElement} />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Follow a ticker</DialogTitle>
          <DialogDescription>
            We&apos;ll pull fundamentals and recent news into your research corpus.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="e.g. RELIANCE"
              autoFocus
              aria-invalid={!!errors.ticker}
              {...tickerField}
              onChange={(event) => {
                event.target.value = event.target.value.toUpperCase()
                onTickerChange(event)
              }}
            />
            <Button type="submit" disabled={isSubmitting || followMutation.isPending}>
              {followMutation.isPending ? "Following…" : "Follow"}
            </Button>
          </div>
          {errors.ticker && <p className="text-xs text-destructive">{errors.ticker.message}</p>}

          <div className="flex flex-wrap gap-1.5 pt-1">
            {SUGGESTED_TICKERS.map((ticker) => (
              <button
                key={ticker}
                type="button"
                onClick={() => setValue("ticker", ticker)}
                className="rounded-full border border-border px-2.5 py-1 font-mono text-[11px] tracking-wide text-muted-foreground transition-colors hover:border-accent-brand hover:text-accent-brand"
              >
                {ticker}
              </button>
            ))}
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
