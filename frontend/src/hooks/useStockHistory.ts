import { useQuery } from '@tanstack/react-query'
import { listTransactions } from '../api/transactions'
import { listDividends } from '../api/dividends'
import type { Transaction } from '../types/transaction'
import type { Dividend } from '../types/dividend'

export type HistoryEntryKind = 'BUY' | 'SELL' | 'DIVIDEND'

export interface HistoryEntry {
  id: string
  kind: HistoryEntryKind
  date: string               // ISO date, for sorting
  shares: number | null      // quantity (tx) or shares_received (div)
  price: number | null       // per-share price (tx only)
  amount: number             // qty*price+fee (tx) or dividend amount
  note: string | null
  raw: Transaction | Dividend
}

export function useStockHistory(ticker: string) {
  const txQuery = useQuery({
    queryKey: ['transactions', ticker],
    queryFn: () => listTransactions({ ticker, include_all: true }),
    enabled: !!ticker,
  })

  const divQuery = useQuery({
    queryKey: ['dividends', ticker],
    queryFn: () => listDividends({ ticker, include_all: true }),
    enabled: !!ticker,
  })

  const entries: HistoryEntry[] = []

  if (txQuery.data) {
    for (const tx of txQuery.data.items) {
      const qty = parseFloat(tx.quantity)
      const prc = parseFloat(tx.price)
      const fee = parseFloat(tx.fee)
      entries.push({
        id: tx.id,
        kind: tx.transaction_type,
        date: tx.transaction_date,
        shares: qty,
        price: prc,
        amount: qty * prc + fee,
        note: tx.note,
        raw: tx,
      })
    }
  }

  if (divQuery.data) {
    for (const div of divQuery.data.items) {
      entries.push({
        id: div.id,
        kind: 'DIVIDEND',
        date: div.ex_dividend_date,
        shares: div.shares_received ? parseFloat(div.shares_received) : null,
        price: null,
        amount: parseFloat(div.amount),
        note: div.note,
        raw: div,
      })
    }
  }

  // Sort newest first
  entries.sort((a, b) => b.date.localeCompare(a.date))

  return {
    entries,
    isLoading: txQuery.isLoading || divQuery.isLoading,
    isError: txQuery.isError || divQuery.isError,
  }
}
