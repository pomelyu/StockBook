export interface Transaction {
  id: string
  ticker: string
  stock_name: string | null
  transaction_type: 'BUY' | 'SELL'
  quantity: string   // Decimal from backend, keep as string to avoid float issues
  price: string
  fee: string
  transaction_date: string  // YYYY-MM-DD
  note: string | null
  created_at: string
  updated_at: string
}

export interface TransactionCreate {
  ticker: string
  transaction_type: 'BUY' | 'SELL'
  quantity: string
  price: string
  fee?: string
  transaction_date: string
  note?: string | null
}

export interface TransactionUpdate {
  transaction_type?: 'BUY' | 'SELL'
  quantity?: string
  price?: string
  fee?: string
  transaction_date?: string
  note?: string | null
}
