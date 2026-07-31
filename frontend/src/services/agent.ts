import api from "./api"
import type { AgentDecision } from "@/types/agent"

export const listAgentDecisions = async (): Promise<AgentDecision[]> => {
  const response = await api.get("/agent/decisions")
  return response.data
}
