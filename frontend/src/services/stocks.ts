import api from "./api"
import type { FollowedStock, StockDetailResponse, StockIngestionResponse, StockUnfollowResponse } from "@/types/stock"

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

export const unfollowStock = async (ticker: string): Promise<StockUnfollowResponse> => {
  const response = await api.post(`/stocks/${ticker}/unfollow`)
  return response.data
}

export const getStockDetail = async (ticker: string): Promise<StockDetailResponse> => {
  const response = await api.get(`/stocks/${ticker}/detail`)
  return response.data
}
