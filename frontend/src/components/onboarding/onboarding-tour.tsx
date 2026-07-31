"use client"

import { useEffect } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { Star, MessageSquare, Quote } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useOnboardingStore } from "@/store/onboarding-store"

const STEPS = [
  {
    icon: Star,
    title: "Follow a ticker",
    body: "Start with an NSE stock like RELIANCE or TCS. We pull its fundamentals and recent news straight into your research corpus.",
  },
  {
    icon: MessageSquare,
    title: "Ask a question",
    body: "“What's the sentiment on TCS this week?” or “Recommend stocks for my profile.” The agent only answers from what's ingested.",
  },
  {
    icon: Quote,
    title: "See it cited",
    body: "Every claim links back to the exact news article or fundamentals row it came from — no invented numbers, ever.",
  },
]

export function OnboardingTour() {
  const hasHydrated = useOnboardingStore((state) => state.hasHydrated)
  const hasSeenOnboarding = useOnboardingStore((state) => state.hasSeenOnboarding)
  const activeStep = useOnboardingStore((state) => state.activeStep)
  const start = useOnboardingStore((state) => state.start)
  const next = useOnboardingStore((state) => state.next)
  const dismiss = useOnboardingStore((state) => state.dismiss)

  useEffect(() => {
    if (!hasHydrated || hasSeenOnboarding) return
    const timer = setTimeout(() => start(), 700)
    return () => clearTimeout(timer)
  }, [hasHydrated, hasSeenOnboarding, start])

  const step = activeStep != null ? STEPS[activeStep] : null

  return (
    <AnimatePresence>
      {step && (
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 12, scale: 0.96 }}
          transition={{ type: "spring", stiffness: 300, damping: 28 }}
          className="fixed bottom-5 left-1/2 z-40 w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 rounded-xl border border-border bg-popover p-4 text-popover-foreground shadow-xl sm:bottom-6 sm:left-auto sm:right-6 sm:translate-x-0"
        >
          <div className="flex items-start gap-3">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-brand/10 text-accent-brand">
              <step.icon className="size-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{step.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{step.body}</p>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between">
            <div className="flex gap-1">
              {STEPS.map((_, index) => (
                <span
                  key={index}
                  className={`h-1 w-4 rounded-full transition-colors ${
                    index === activeStep ? "bg-accent-brand" : "bg-muted"
                  }`}
                />
              ))}
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={dismiss}>
                Skip
              </Button>
              <Button size="sm" onClick={() => next(STEPS.length)}>
                {activeStep === STEPS.length - 1 ? "Got it" : "Next"}
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
