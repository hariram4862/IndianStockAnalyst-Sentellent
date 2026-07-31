import api from "./api"
import type { AlertRule, AlertRuleType, TriggeredAlert } from "@/types/agent"

export const listAlertRules = async (): Promise<AlertRule[]> => {
  const response = await api.get("/alerts")
  return response.data
}

export const createAlertRule = async (
  ticker: string,
  ruleType: AlertRuleType,
  threshold?: number | null
): Promise<AlertRule> => {
  const response = await api.post("/alerts", { ticker, rule_type: ruleType, threshold: threshold ?? null })
  return response.data
}

export const deleteAlertRule = async (id: number): Promise<void> => {
  await api.delete(`/alerts/${id}`)
}

export const listNotifications = async (): Promise<TriggeredAlert[]> => {
  const response = await api.get("/alerts/notifications")
  return response.data
}

export const markNotificationsRead = async (): Promise<void> => {
  await api.post("/alerts/notifications/read")
}
