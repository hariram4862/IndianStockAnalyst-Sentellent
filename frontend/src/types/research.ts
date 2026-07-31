export interface Citation {
  ticker: string
  title: string
  source_type: string
  url: string | null
  published_at: string | null
  snippet: string
  sentiment_label: string | null
  sentiment_score: number | null
  impact_label: string | null
  event_type: string | null
  similarity_score: number | null
}

export interface ChatResponse {
  session_id: number
  answer: string
  citations: Citation[]
  persona_summary: string | null
}
