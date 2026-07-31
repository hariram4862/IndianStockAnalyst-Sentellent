export interface StockSummary {
  id: number
  ticker: string
  company_name: string
  exchange: string
  sector: string | null
  industry: string | null
  current_price_inr: number | null
  market_cap_inr: number | null
  pe_ratio: number | null
  dividend_yield: number | null
  debt_to_equity: number | null
  fundamentals_summary: string | null
  rolling_sentiment_label: string | null
  rolling_sentiment_score: number | null
}

export interface FollowedStock {
  id: number
  is_active: boolean
  followed_at: string
  last_ingested_at: string | null
  stock: StockSummary
}

export interface StockIngestionResponse {
  followed_stock: FollowedStock
  ingested_documents: number
  ingested_chunks: number
  message: string
}

export interface StockUnfollowResponse {
  ticker: string
  message: string
}

export interface StockDetailDocument {
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

export interface StockDetailResponse {
  stock: StockSummary
  is_followed: boolean
  followed_at: string | null
  last_ingested_at: string | null
  documents: StockDetailDocument[]
}
