"use client"

import { motion } from "framer-motion"

export function LivePill({ lastUpdated }: { lastUpdated: Date | undefined }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <motion.span
        className="size-1.5 rounded-full bg-positive"
        animate={{ opacity: [1, 0.3, 1] }}
        transition={{ duration: 1.6, repeat: Infinity }}
      />
      {lastUpdated
        ? `Updated ${lastUpdated.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`
        : "Live"}
    </span>
  )
}
