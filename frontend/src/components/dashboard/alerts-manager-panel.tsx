"use client"

import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Bell, Pencil, X } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { getErrorMessage } from "@/lib/errors"
import { RULE_LABELS, ruleSummary } from "@/lib/alert-rules"
import { cn } from "@/lib/utils"
import { createAlertRule, deleteAlertRule, listAlertRules } from "@/services/alerts"
import { listFollowedStocks } from "@/services/stocks"
import type { AlertRule, AlertRuleType } from "@/types/agent"

const selectClass = cn(
  "h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none",
  "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
)

export function AlertsManagerPanel() {
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [ticker, setTicker] = useState("")
  const [ruleType, setRuleType] = useState<AlertRuleType>("negative_sentiment")
  const [threshold, setThreshold] = useState("")

  const rulesQuery = useQuery({ queryKey: ["alert-rules"], queryFn: listAlertRules })
  const stocksQuery = useQuery({ queryKey: ["followed-stocks"], queryFn: listFollowedStocks })

  const rules = rulesQuery.data ?? []
  const followed = stocksQuery.data ?? []

  function resetForm() {
    setEditingId(null)
    setTicker("")
    setRuleType("negative_sentiment")
    setThreshold("")
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingId != null) {
        await deleteAlertRule(editingId)
      }
      return createAlertRule(ticker, ruleType, ruleType === "debt_threshold" ? Number(threshold) : null)
    },
    onSuccess: () => {
      toast.success(editingId != null ? "Alert updated." : "Alert created.")
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] })
      resetForm()
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not save alert.")),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAlertRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] })
      resetForm()
    },
    onError: (error) => toast.error(getErrorMessage(error, "Could not remove alert.")),
  })

  function startEdit(rule: AlertRule) {
    setEditingId(rule.id)
    setTicker(rule.ticker)
    setRuleType(rule.rule_type)
    setThreshold(rule.threshold != null ? String(rule.threshold) : "")
  }

  const thresholdMissing = ruleType === "debt_threshold" && !threshold.trim()
  const canSave = !!ticker && !thresholdMissing

  return (
    <section className="space-y-3 rounded-xl border border-border p-4">
      <h2 className="text-sm font-semibold">Manage alerts</h2>

      {rulesQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : (
        <div className="space-y-1.5">
          {rules.map((rule) => (
            <div
              key={rule.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm"
            >
              <span className="flex min-w-0 items-center gap-1.5 text-muted-foreground">
                <Bell className="size-3.5 shrink-0" />
                <span className="truncate">
                  <span className="font-mono font-medium text-foreground">{rule.ticker}</span> — {ruleSummary(rule)}
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-1">
                <button
                  type="button"
                  onClick={() => startEdit(rule)}
                  className="text-muted-foreground hover:text-accent-brand"
                  aria-label="Edit alert"
                >
                  <Pencil className="size-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(rule.id)}
                  className="text-muted-foreground hover:text-destructive"
                  aria-label="Remove alert"
                >
                  <X className="size-3.5" />
                </button>
              </span>
            </div>
          ))}
          {!rulesQuery.isLoading && rules.length === 0 && (
            <p className="text-xs text-muted-foreground">No alerts set yet.</p>
          )}
        </div>
      )}

      <div className="space-y-2 border-t border-border pt-3">
        {editingId != null && (
          <p className="text-[11px] font-medium text-accent-brand">Editing alert — save to replace it.</p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <select value={ticker} onChange={(event) => setTicker(event.target.value)} className={selectClass}>
            <option value="" disabled>
              Select stock
            </option>
            {followed.map((f) => (
              <option key={f.stock.ticker} value={f.stock.ticker}>
                {f.stock.ticker}
              </option>
            ))}
          </select>
          <select
            value={ruleType}
            onChange={(event) => setRuleType(event.target.value as AlertRuleType)}
            className={selectClass}
          >
            {Object.entries(RULE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {ruleType === "debt_threshold" && (
            <Input
              type="number"
              step="0.1"
              value={threshold}
              onChange={(event) => setThreshold(event.target.value)}
              placeholder="e.g. 1.5"
              className="w-24"
            />
          )}
        </div>
        <div className="flex justify-end gap-2">
          {editingId != null && (
            <Button size="sm" variant="ghost" onClick={resetForm}>
              Cancel
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || !canSave}
          >
            <Bell className="size-3.5" /> {editingId != null ? "Save" : "Add"}
          </Button>
        </div>
      </div>
    </section>
  )
}
