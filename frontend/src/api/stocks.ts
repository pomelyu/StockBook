import client from './client'
import type { Stock } from '../types/watchlist'

export async function searchStocks(q: string): Promise<Stock[]> {
  const res = await client.get<Stock[]>(`/stocks/search?q=${encodeURIComponent(q)}`)
  return res.data
}

export async function batchGetPrices(tickers: string[]): Promise<Record<string, Stock>> {
  if (tickers.length === 0) return {}
  const res = await client.get<Record<string, Stock>>(
    `/stocks/prices?tickers=${tickers.map(encodeURIComponent).join(',')}`
  )
  return res.data
}
