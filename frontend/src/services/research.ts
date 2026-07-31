import api from "./api"
import type { ChatMessage, ChatResponse, ChatSessionSummary, Persona } from "@/types/research"

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

export const listSessions = async (): Promise<ChatSessionSummary[]> => {
  const response = await api.get("/research/sessions")
  return response.data
}

export const getSessionMessages = async (sessionId: number): Promise<ChatMessage[]> => {
  const response = await api.get(`/research/sessions/${sessionId}/messages`)
  return response.data
}

export const getPersona = async (): Promise<Persona> => {
  const response = await api.get("/research/persona")
  return response.data
}
