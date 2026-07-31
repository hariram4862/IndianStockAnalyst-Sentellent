"use client"

import { motion } from "framer-motion"

import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { useStockDetailStore } from "@/store/stock-detail-store"
import type { RankedStock } from "@/types/research"

function ScoreRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>{label}</span>
        <span className="font-mono">{Math.round(value * 100)}</span>
      </div>
      <Progress value={value * 100} />
    </div>
  )
}

export function RecommendationCards({ picks }: { picks: RankedStock[] }) {
  const openStockDetail = useStockDetailStore((state) => state.open)

  if (picks.length === 0) return null

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {picks.map((pick, index) => (
        <motion.button
          key={pick.ticker}
          type="button"
          onClick={() => openStockDetail(pick.ticker)}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: index * 0.07 }}
          className="space-y-3 rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-accent-brand/40"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold">{pick.ticker}</span>
              <Badge variant="accent">#{index + 1}</Badge>
            </div>
            <span className="font-mono text-sm font-semibold">{(pick.composite_score * 100).toFixed(0)}</span>
          </div>
          <p className="truncate text-xs text-muted-foreground">{pick.company_name}</p>

          <div className="space-y-2">
            <ScoreRow label="Value" value={pick.value_score} />
            <ScoreRow label="Stability" value={pick.stability_score} />
            <ScoreRow label="Momentum" value={pick.momentum_score} />
          </div>

          <p className="text-xs leading-relaxed text-muted-foreground">{pick.reason}</p>
        </motion.button>
      ))}
    </div>
  )
}
