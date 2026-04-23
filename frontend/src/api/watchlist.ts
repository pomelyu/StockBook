import client from './client'
import type { WatchlistItem } from '../types/watchlist'

export async function getWatchlist(): Promise<WatchlistItem[]> {
  const res = await client.get<WatchlistItem[]>('/watchlist/')
  return res.data
}

export async function addToWatchlist(ticker: string, note?: string): Promise<WatchlistItem> {
  const res = await client.post<WatchlistItem>('/watchlist/', { ticker, note })
  return res.data
}

export async function removeFromWatchlist(ticker: string): Promise<void> {
  await client.delete(`/watchlist/${ticker}`)
}

export { searchStocks } from './stocks'
