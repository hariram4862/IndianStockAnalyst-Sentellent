export type AlertRuleType = "negative_sentiment" | "positive_sentiment" | "debt_threshold"

export interface AlertRule {
  id: number
  ticker: string
  company_name: string
  rule_type: AlertRuleType
  threshold: number | null
  is_active: boolean
  last_triggered_at: string | null
  created_at: string
}

export interface TriggeredAlert {
  id: number
  ticker: string
  message: string
  is_read: boolean
  created_at: string
}

export type AgentDecisionAction = "buy" | "hold" | "avoid"

export interface AgentDecision {
  id: number
  ticker: string
  company_name: string
  action: AgentDecisionAction
  reasoning: string
  composite_score: number
  price_at_decision_inr: number | null
  current_price_inr: number | null
  created_at: string
}
