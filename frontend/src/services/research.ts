import api from "./api"
import type { ChatResponse } from "@/types/research"

export const sendResearchMessage = async (
  message: string,
  sessionId?: number | null
): Promise<ChatResponse> => {
  const response = await api.post("/research/chat", {
    message,
    session_id: sessionId ?? null,
  })
  return response.data
}
