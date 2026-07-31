export interface IndexQuote {
  name: string
  symbol: string
  price: number
  change: number
  change_percent: number
}

export interface IndexIntradayPoint {
  time: string
  price: number
}

export interface MarketMover {
  ticker: string
  price: number
  change_percent: number
}

export interface MarketMovers {
  gainers: MarketMover[]
  losers: MarketMover[]
}

export interface MarketHeadline {
  title: string
  url: string
  source_name: string
  published_at: string | null
}
