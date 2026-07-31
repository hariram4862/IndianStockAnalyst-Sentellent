import type { AlertRule, AlertRuleType } from "@/types/agent"

export const RULE_LABELS: Record<AlertRuleType, string> = {
  negative_sentiment: "Sentiment turns negative",
  positive_sentiment: "Sentiment turns positive",
  debt_threshold: "Debt/Equity exceeds",
}

export function ruleSummary(rule: AlertRule): string {
  if (rule.rule_type === "debt_threshold") return `Debt/Equity exceeds ${rule.threshold}`
  return RULE_LABELS[rule.rule_type]
}
