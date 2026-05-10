export type DividendType = 'CASH' | 'STOCK' | 'DRIP'

export interface Dividend {
  id: string
  ticker: string
  stock_name: string | null
  dividend_type: DividendType
  amount: string       // Decimal from backend
  currency: string
  shares_received: string | null
  ex_dividend_date: string  // YYYY-MM-DD
  payment_date: string | null
  note: string | null
  account_id: string
  account_name: string
  created_at: string
}

export interface DividendCreate {
  ticker: string
  dividend_type: DividendType
  amount: string
  currency: string
  shares_received?: string | null
  ex_dividend_date: string
  payment_date?: string | null
  note?: string | null
  account_id: string
}

export interface DividendUpdate {
  dividend_type?: DividendType
  amount?: string
  currency?: string
  shares_received?: string | null
  ex_dividend_date?: string
  payment_date?: string | null
  note?: string | null
  account_id?: string | null
}
