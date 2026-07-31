import api from "./api"
import type { IndexIntradayPoint, IndexQuote, MarketHeadline, MarketMovers } from "@/types/market"

export const getIndexQuotes = async (): Promise<IndexQuote[]> => {
  const response = await api.get("/market/indices")
  return response.data
}

export const getIndexIntraday = async (symbol: string): Promise<IndexIntradayPoint[]> => {
  const response = await api.get(`/market/indices/${symbol}/intraday`)
  return response.data
}

export const getMarketMovers = async (): Promise<MarketMovers> => {
  const response = await api.get("/market/movers")
  return response.data
}

export const getMarketNews = async (): Promise<MarketHeadline[]> => {
  const response = await api.get("/market/news")
  return response.data
}
