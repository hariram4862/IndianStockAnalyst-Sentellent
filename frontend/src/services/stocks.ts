import api from "./api"
import type { FollowedStock, StockIngestionResponse } from "@/types/stock"

export const listFollowedStocks = async (): Promise<FollowedStock[]> => {
  const response = await api.get("/stocks/followed")
  return response.data
}

export const followStock = async (
  ticker: string
): Promise<StockIngestionResponse> => {
  const response = await api.post("/stocks/follow", {
    ticker,
  })
  return response.data
}

export const refreshStock = async (
  ticker: string
): Promise<StockIngestionResponse> => {
  const response = await api.post(`/stocks/${ticker}/refresh`)
  return response.data
}
