export interface WatchlistItem {
  id: string
  ticker: string
  name: string | null
  market: 'TW' | 'US'
  currency: 'TWD' | 'USD'
  last_price: number | null
  price_updated_at: string | null
  note: string | null
  added_at: string
}

export interface Stock {
  id: string
  ticker: string
  name: string | null
  market: string
  currency: string
  last_price: number | null
  price_updated_at: string | null
}
