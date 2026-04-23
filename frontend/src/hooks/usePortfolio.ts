import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listAllTransactions } from '../api/transactions'
import { listAllDividends } from '../api/dividends'
import { batchGetPrices } from '../api/stocks'
import { calculatePortfolio } from '../utils/pnl'
import type { PortfolioSummary } from '../utils/pnl'
import { getMarketUpdateTimes } from '../utils/marketTime'

export function usePortfolio(): {
  data: PortfolioSummary | undefined
  isLoading: boolean
  isError: boolean
  refetch: () => void
  marketUpdateTimes: { us: string | null; tw: string | null }
} {
  const queryClient = useQueryClient()

  const txQuery = useQuery({
    queryKey: ['transactions', 'all'],
    queryFn: listAllTransactions,
    staleTime: 30_000,
  })

  const divQuery = useQuery({
    queryKey: ['dividends', 'all'],
    queryFn: listAllDividends,
    staleTime: 30_000,
  })

  // Extract unique tickers from transactions and dividends
  const transactions = txQuery.data ?? []
  const dividends = divQuery.data ?? []
  const tickers = [...new Set([
    ...transactions.map(tx => tx.ticker),
    ...dividends.map(div => div.ticker),
  ])]

  const pricesQuery = useQuery({
    queryKey: ['prices', tickers.sort().join(',')],
    queryFn: () => batchGetPrices(tickers),
    enabled: tickers.length > 0,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  const isLoading = txQuery.isLoading || divQuery.isLoading || (tickers.length > 0 && pricesQuery.isLoading)
  const isError = txQuery.isError || divQuery.isError

  const prices: Record<string, { last_price: number | null; currency: string; name?: string | null }> = {}
  if (pricesQuery.data) {
    for (const [ticker, stock] of Object.entries(pricesQuery.data)) {
      prices[ticker] = { last_price: stock.last_price, currency: stock.currency, name: stock.name }
    }
  }

  const data =
    !isLoading && !isError
      ? calculatePortfolio(transactions, dividends, prices)
      : undefined

  const marketUpdateTimes = getMarketUpdateTimes(
    Object.entries(pricesQuery.data ?? {}).map(([ticker, stock]) => ({
      price_updated_at: stock.price_updated_at ?? null,
      isTW: ticker.endsWith('.TW'),
    }))
  )

  function refetch() {
    queryClient.invalidateQueries({ queryKey: ['transactions', 'all'] })
    queryClient.invalidateQueries({ queryKey: ['dividends', 'all'] })
    queryClient.invalidateQueries({ queryKey: ['prices'] })
  }

  return { data, isLoading, isError, refetch, marketUpdateTimes }
}
