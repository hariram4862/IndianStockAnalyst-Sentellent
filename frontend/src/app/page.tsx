"use client"

import { useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import {
  ArrowRight,
  BadgeIndianRupee,
  Gauge,
  MessageSquareQuote,
  ShieldCheck,
  Sparkles,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/store/auth-store"

const FEATURES = [
  {
    icon: MessageSquareQuote,
    title: "Grounded & cited",
    body: "Every claim, number, and recommendation links back to the exact news article or fundamentals row it came from. If it's not in the ingested data, the agent says so — never invents it.",
  },
  {
    icon: Sparkles,
    title: "Dynamic investor memory",
    body: "Tell it once — \"I'm a conservative, dividend-focused investor and I avoid high-debt companies\" — and it remembers, updating your persona from chat and from what it reads.",
  },
  {
    icon: BadgeIndianRupee,
    title: "Priced in INR",
    body: "Fundamentals, market cap, and every figure the agent quotes are sourced from NSE/BSE data and shown in rupees — no unit confusion.",
  },
  {
    icon: Gauge,
    title: "Efficient, persona-based ranking",
    body: "Stocks are scored against your profile — value, stability, momentum — with deterministic, testable logic. No brute-force LLM call per stock per query.",
  },
]

const STEPS = [
  { step: "01", title: "Follow a ticker", body: "Add an NSE/BSE stock like RELIANCE or TCS." },
  { step: "02", title: "Ingest & embed", body: "Fundamentals and recent news are chunked, embedded, and sentiment-tagged." },
  { step: "03", title: "Ask a question", body: "\"What's the sentiment on TCS this week?\" or \"Recommend stocks for my profile.\"" },
  { step: "04", title: "Get a cited answer", body: "Grounded, numbered citations back to the source — every time." },
]

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
}

export default function LandingPage() {
  const router = useRouter()
  const { token, hasHydrated } = useAuthStore()

  useEffect(() => {
    if (hasHydrated && token) router.replace("/dashboard")
  }, [router, token, hasHydrated])

  if (!hasHydrated || token) return null

  return (
    <main className="min-h-svh bg-background text-foreground">
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-background/85 px-6 py-4 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-md bg-accent-brand font-mono text-sm font-semibold text-accent-brand-foreground">
            IA
          </div>
          <span className="text-sm font-medium">Indian Stock Analyst</span>
        </div>
        <Button render={<Link href="/login" />} size="sm" variant="outline">
          Log in
        </Button>
      </header>

      <section className="mx-auto max-w-4xl px-6 pt-20 pb-16 text-center sm:pt-28">
        <motion.div initial="hidden" animate="show" variants={fadeUp} transition={{ duration: 0.5 }}>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs font-medium text-muted-foreground">
            <ShieldCheck className="size-3.5" /> Grounded RAG, not a chatbot with opinions
          </span>
        </motion.div>
        <motion.h1
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ duration: 0.5, delay: 0.08 }}
          className="mt-6 text-3xl font-semibold tracking-tight sm:text-5xl"
        >
          Your Personal AI Equity Research{" "}
          <span className="text-accent-brand">Chief of Staff</span>
          {" "}for the NSE &amp; BSE
        </motion.h1>
        <motion.p
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ duration: 0.5, delay: 0.16 }}
          className="mx-auto mt-5 max-w-2xl text-base text-muted-foreground sm:text-lg"
        >
          Follow Indian tickers, and it ingests fundamentals and recent news into a vector store.
          Chat to research and get personalised ideas — every number cited, every figure in INR.
        </motion.p>
        <motion.div
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ duration: 0.5, delay: 0.24 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Button render={<Link href="/login" />} size="lg" className="gap-2">
            Get started <ArrowRight className="size-4" />
          </Button>
          <Button render={<a href="#how-it-works" />} size="lg" variant="outline">
            See how it works
          </Button>
        </motion.div>
      </section>

      <section className="border-y border-border bg-muted/30 py-16">
        <div className="mx-auto max-w-5xl px-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {FEATURES.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.4, delay: index * 0.06 }}
                className="rounded-xl border border-border bg-card p-6"
              >
                <feature.icon className="size-5 text-accent-brand" />
                <h3 className="mt-3 text-sm font-semibold">{feature.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{feature.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-5xl px-6 py-20">
        <motion.h2
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center text-2xl font-semibold"
        >
          How it works
        </motion.h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((item, index) => (
            <motion.div
              key={item.step}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.4, delay: index * 0.08 }}
            >
              <span className="font-mono text-xs text-accent-brand">{item.step}</span>
              <h3 className="mt-2 text-sm font-semibold">{item.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{item.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="border-t border-border bg-muted/30">
        <div className="mx-auto max-w-3xl px-6 py-16 text-center">
          <h2 className="text-2xl font-semibold">Ready to research smarter?</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in with Google and follow your first ticker in under a minute.
          </p>
          <Button render={<Link href="/login" />} size="lg" className="mt-6 gap-2">
            Get started <ArrowRight className="size-4" />
          </Button>
        </div>
      </section>

      <footer className="border-t border-border px-6 py-6 text-center text-xs text-muted-foreground">
        Built for the Sentellent Hiring Challenge — figures in INR, answers grounded in retrieved sources.
      </footer>
    </main>
  )
}
