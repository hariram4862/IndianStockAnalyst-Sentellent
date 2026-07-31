import { create } from "zustand"

interface StockDetailState {
  ticker: string | null
  open: (ticker: string) => void
  close: () => void
}

export const useStockDetailStore = create<StockDetailState>((set) => ({
  ticker: null,
  open: (ticker) => set({ ticker }),
  close: () => set({ ticker: null }),
}))
